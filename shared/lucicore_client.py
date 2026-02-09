"""
Единый асинхронный HTTP-клиент для всех ботов LUCICORE.

Оборачивает все эндпоинты LUCICORE API: пользователей (по ``hash_id``
и числовому ``id``), Merchant / Web Client API, проверку здоровья.

Использование:
    from shared.lucicore_client import LucicoreClient

    async with LucicoreClient(base_url="http://127.0.0.1:8000", api_token="...") as client:
        health = await client.health()
        users  = await client.get_users()
        user   = await client.get_user_by_hash("Kf3xQ7pLmN8w0Zv1cYtBgA")
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Настройки по умолчанию
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT = 30.0        # секунд на запрос
_MAX_RETRIES = 3               # автоматические повторы при временных ошибках
_RETRY_BACKOFF = 0.5           # базовая задержка между повторами (секунды)

# HTTP-коды, при которых имеет смысл повторить запрос
_RETRYABLE_STATUS = frozenset({502, 503, 504})


class LucicoreAPIError(Exception):
    """Исключение при ошибочном ответе LUCICORE API.

    Атрибуты:
        status_code: HTTP-код ответа.
        detail:      Текст ошибки из тела ответа.
    """

    def __init__(self, status_code: int, detail: str | None = None):
        self.status_code = status_code
        self.detail = detail or f"HTTP {status_code}"
        super().__init__(self.detail)


class LucicoreClient:
    """Асинхронный HTTP-клиент, оборачивающий все эндпоинты LUCICORE API.

    Поддерживает автоматический retry при транспортных ошибках и кодах 502/503/504.
    Является async-контекстным менеджером.

    Аргументы конструктора:
        base_url:    Базовый URL сервера (по умолчанию ``http://127.0.0.1:8000``).
        api_token:   Bearer-токен бота (опционально).
        timeout:     Тайм-аут на запрос в секундах (по умолчанию 30).
        max_retries: Количество повторных попыток (по умолчанию 3).
    """

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_token: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        transport = httpx.AsyncHTTPTransport(retries=max_retries)
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout),
            transport=transport,
        )
        self._max_retries = max_retries

    async def __aenter__(self) -> "LucicoreClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Закрыть пул HTTP-соединений."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Внутренние хелперы
    # ------------------------------------------------------------------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        """Отправить HTTP-запрос с логикой повторов при временных сбоях."""
        import asyncio

        last_exc: BaseException | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                )
                if resp.status_code in _RETRYABLE_STATUS and attempt < self._max_retries:
                    logger.warning(
                        "LUCICORE %s %s вернул %s (попытка %d/%d), повтор…",
                        method, path, resp.status_code, attempt, self._max_retries,
                    )
                    await asyncio.sleep(_RETRY_BACKOFF * attempt)
                    continue

                if resp.status_code >= 400:
                    detail = None
                    try:
                        body = resp.json()
                        detail = body.get("detail") if isinstance(body, dict) else str(body)
                    except Exception:
                        detail = resp.text
                    raise LucicoreAPIError(resp.status_code, detail)

                # 204 No Content или DELETE с пустым телом
                if resp.status_code == 204 or not resp.content:
                    return None

                return resp.json()

            except httpx.TransportError as exc:
                last_exc = exc
                logger.warning(
                    "LUCICORE %s %s транспортная ошибка (попытка %d/%d): %s",
                    method, path, attempt, self._max_retries, exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(_RETRY_BACKOFF * attempt)
                    continue
                raise

        raise last_exc  # type: ignore[misc]

    # Удобные обёртки
    async def _get(self, path: str, **kwargs: Any) -> Any:
        """Выполнить GET-запрос."""
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, **kwargs: Any) -> Any:
        """Выполнить POST-запрос."""
        return await self._request("POST", path, **kwargs)

    async def _put(self, path: str, **kwargs: Any) -> Any:
        """Выполнить PUT-запрос."""
        return await self._request("PUT", path, **kwargs)

    async def _delete(self, path: str, **kwargs: Any) -> Any:
        """Выполнить DELETE-запрос."""
        return await self._request("DELETE", path, **kwargs)

    # ==================================================================
    # Проверка здоровья
    # ==================================================================
    async def health(self) -> Dict[str, Any]:
        """Проверить доступность API.

        Возвращает:
            ``{"status": "healthy"}`` при успехе.
        """
        return await self._get("/health")

    # ==================================================================
    # Пользователи — по числовому ID (внутренний)
    # ==================================================================
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список пользователей с пагинацией.

        Аргументы:
            skip:  Пропустить N записей (по умолчанию 0).
            limit: Максимум записей (по умолчанию 100).

        Возвращает:
            Список словарей с данными пользователей (включая ``hash_id``).
        """
        return await self._get("/users/", params={"skip": skip, "limit": limit})

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Получить пользователя по числовому ID.

        Аргументы:
            user_id: Числовой первичный ключ.
        """
        return await self._get(f"/users/{user_id}")

    async def create_user(self, *, login: str, username: str, password: str, **kwargs: Any) -> Dict[str, Any]:
        """Создать нового пользователя.

        ``hash_id`` генерируется сервером автоматически и возвращается в ответе.

        Аргументы:
            login:    Уникальный логин пользователя.
            username: Уникальное имя пользователя.
            password: Пароль в открытом виде.
            **kwargs: Дополнительные поля (email, display_name, avatar).

        Возвращает:
            Словарь с данными созданного пользователя (включая ``hash_id``).
        """
        payload = {"login": login, "username": username, "password": password, **kwargs}
        return await self._post("/users/", json=payload)

    async def update_user(self, user_id: int, **fields: Any) -> Dict[str, Any]:
        """Обновить пользователя по числовому ID.

        Аргументы:
            user_id:  Числовой первичный ключ.
            **fields: Поля для обновления.
        """
        return await self._put(f"/users/{user_id}", json=fields)

    async def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Удалить пользователя по числовому ID.

        Аргументы:
            user_id: Числовой первичный ключ.
        """
        return await self._delete(f"/users/{user_id}")

    # ==================================================================
    # Пользователи — по HASH-идентификатору (основной способ)
    # ==================================================================
    async def get_user_by_hash(self, hash_id: str) -> Dict[str, Any]:
        """Получить пользователя по публичному HASH-идентификатору.

        Это основной и рекомендуемый способ идентификации пользователей.

        Аргументы:
            hash_id: UUID v4 идентификатор (36 символов).

        Возвращает:
            Словарь с данными пользователя.

        Исключения:
            LucicoreAPIError: 404 если пользователь не найден.
        """
        return await self._get(f"/users/hash/{hash_id}")

    async def update_user_by_hash(self, hash_id: str, **fields: Any) -> Dict[str, Any]:
        """Обновить пользователя по UUID v4 идентификатору.

        Аргументы:
            hash_id:  UUID v4 идентификатор.
            **fields: Поля для обновления.

        Возвращает:
            Словарь с обновлёнными данными пользователя.
        """
        return await self._put(f"/users/hash/{hash_id}", json=fields)

    async def delete_user_by_hash(self, hash_id: str) -> Dict[str, Any]:
        """Удалить пользователя по UUID v4 идентификатору.

        Аргументы:
            hash_id: UUID v4 идентификатор.

        Возвращает:
            ``{"message": "Пользователь успешно удалён"}``.
        """
        return await self._delete(f"/users/hash/{hash_id}")

    # ==================================================================
    # Merchant / Web Client API
    # ==================================================================
    async def get_captcha(self) -> Dict[str, Any]:
        """Получить капчу для регистрации/входа в Web Client API.

        Возвращает:
            Словарь с ``captcha_id`` и ``image`` (base64).
        """
        return await self._get("/merchant/captcha")

    async def register_merchant(
        self, user_id: int, *, captcha_id: str, captcha_answer: str
    ) -> Dict[str, Any]:
        """Зарегистрировать пользователя в Web Client API.

        Аргументы:
            user_id:        Числовой ID пользователя.
            captcha_id:     Идентификатор капчи.
            captcha_answer: Ответ на капчу.

        Возвращает:
            Словарь с ``hash_id``, ``merchant_client_id``, ``auth_code``.
        """
        return await self._post(
            f"/users/{user_id}/merchant/register",
            json={"captcha_id": captcha_id, "captcha_answer": captcha_answer},
        )

    async def sync_merchant(self, user_id: int) -> Dict[str, Any]:
        """Синхронизировать профиль пользователя из Web Client API.

        Аргументы:
            user_id: Числовой ID пользователя.

        Возвращает:
            Обновлённые данные пользователя.
        """
        return await self._post(f"/users/{user_id}/merchant/sync")
