"""
Утилиты безопасности LUCICORE.

Модуль содержит:
    • Хеширование паролей (PBKDF2-SHA256)
    • Генерация уникальных HASH-идентификаторов (вместо числовых ID)
    • Генерация API-токенов
    • Bearer-аутентификация ботов
"""
import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Хеширование паролей
# ---------------------------------------------------------------------------
_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "100000"))


def hash_password(password: str) -> str:
    """Хешировать пароль алгоритмом PBKDF2-SHA256 со случайной солью.

    Аргументы:
        password: Пароль в открытом виде.

    Возвращает:
        Base64-строку ``salt(16 байт) + digest(32 байта)``.

    Исключения:
        ValueError: Если пароль пустой.
    """
    if not password:
        raise ValueError("Пароль не может быть пустым")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return base64.b64encode(salt + digest).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверить пароль по сохранённому хешу.

    Аргументы:
        password:    Пароль в открытом виде.
        stored_hash: Ранее сохранённый хеш (результат ``hash_password``).

    Возвращает:
        ``True`` если пароль верный, ``False`` иначе.
    """
    raw = base64.b64decode(stored_hash.encode("ascii"))
    salt = raw[:16]
    digest = raw[16:]
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return hmac.compare_digest(digest, check)


# ---------------------------------------------------------------------------
# Генерация уникальных HASH-идентификаторов
# ---------------------------------------------------------------------------

def generate_hash_id() -> str:
    """Сгенерировать уникальный идентификатор пользователя (UUID v4).

    Используется как публичный идентификатор пользователя вместо
    последовательного числового ID.  Результат — каноническая строка
    UUID v4 длиной 36 символов (8-4-4-4-12).

    Возвращает:
        Строку UUID v4 (например ``'550e8400-e29b-41d4-a716-446655440000'``).
    """
    return str(uuid.uuid4())


def generate_deterministic_hash(*parts: str, length: int = 16) -> str:
    """Сгенерировать детерминированный хеш из переданных строк.

    В отличие от ``generate_hash_id``, при одинаковых входных данных
    всегда возвращает одинаковый результат.  Полезно, когда нужно
    воспроизводимо вычислить идентификатор из известных полей.

    Аргументы:
        *parts:  Произвольные строки, которые будут склеены через ``:``
                 и захешированы SHA-256.
        length:  Длина выходной hex-строки (по умолчанию 16 символов).
                 Максимум 64 (полный SHA-256 дайджест).

    Возвращает:
        Hex-строку длиной ``length`` символов.

    Пример:
        >>> generate_deterministic_hash("user", "42")
        'a3f1b9c8e7d24056'
    """
    data = ":".join(parts).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    return digest[:length]


def generate_composite_hash(user_id: int | str | None = None) -> str:
    """Сгенерировать составной уникальный хеш.

    Комбинирует случайные байты с наносекундной меткой времени,
    а при указании ``user_id`` — подмешивает его в хеш для
    дополнительной привязки к сущности.

    Аргументы:
        user_id: Необязательный идентификатор пользователя для подмешивания.

    Возвращает:
        Hex-строку длиной 16 символов.

    Пример:
        >>> generate_composite_hash(42)
        'b7e4f19a3c5d820e'
    """
    random_part = secrets.token_bytes(8)
    time_part = str(time.time_ns()).encode("utf-8")
    seed = random_part + time_part
    if user_id is not None:
        seed += str(user_id).encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:16]


# ---------------------------------------------------------------------------
# API-токены
# ---------------------------------------------------------------------------

def generate_api_token() -> str:
    """Сгенерировать криптографически стойкий случайный API-токен.

    Возвращает:
        URL-safe строку длиной 43 символа.
    """
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Bearer-аутентификация ботов
# ---------------------------------------------------------------------------

def _load_valid_tokens() -> dict[str, str]:
    """Загрузить API-токены ботов из переменных окружения.

    Ищет переменные вида ``BOT_*_API_TOKEN`` и формирует маппинг
    ``{токен: имя_бота}``.  Пустые значения игнорируются.

    Возвращает:
        Словарь ``{token: bot_name}``.
    """
    token_env_vars = {
        "BOT_SALES_API_TOKEN": "bot_sales",
        "BOT_ADMIN_API_TOKEN": "bot_admin",
        "BOT_SUPPORT_API_TOKEN": "bot_support",
        "BOT_NOTIFY_API_TOKEN": "bot_notify",
    }
    tokens: dict[str, str] = {}
    for env_var, name in token_env_vars.items():
        value = os.getenv(env_var, "").strip()
        if value:
            tokens[value] = name
    return tokens


# Переиспользуемая схема безопасности FastAPI
_bearer_scheme = HTTPBearer(auto_error=False)


async def require_bot_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    """FastAPI-зависимость: требует валидный заголовок ``Authorization: Bearer <token>``.

    Возвращает:
        Имя бота (например ``"bot_sales"``).

    Исключения:
        HTTPException 401: Заголовок отсутствует.
        HTTPException 403: Токен невалидный.

    Примечание:
        Если ни одна переменная ``BOT_*_API_TOKEN`` не задана — аутентификация
        отключена (dev-режим), возвращается ``"anonymous"``.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует заголовок Authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )

    valid_tokens = _load_valid_tokens()

    # Если токены не настроены — разрешаем (dev-режим).
    if not valid_tokens:
        logger.warning("BOT_*_API_TOKEN не настроены — аутентификация отключена (dev-режим)")
        return "anonymous"

    bot_name = valid_tokens.get(credentials.credentials)
    if bot_name is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалидный API-токен",
        )

    return bot_name


async def optional_bot_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """Аналог ``require_bot_token``, но не требует наличия заголовка.

    Возвращает ``None`` если заголовок Authorization отсутствует.
    Полезно для публичных эндпоинтов (``/health``), которые опционально
    идентифицируют вызывающего.
    """
    if credentials is None:
        return None
    valid_tokens = _load_valid_tokens()
    return valid_tokens.get(credentials.credentials)
