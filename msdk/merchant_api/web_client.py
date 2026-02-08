"""
Web Client API SDK - Клиент для веб-авторизации покупателей.

Двухуровневая авторизация:
- Authorization: Bearer <MerchantApiKey> - для всех запросов
- X-Client-Session: <session_token> - для защищённых endpoints (после login/register)
"""

import requests


# =============================================================================
# Статусы заявок
# =============================================================================

class DepositStatus:
    """
    Статусы заявок на пополнение (ClientDepositRequest).

    Жизненный цикл:
        created -> creds_at -> waiting_at -> payed_at -> done_at
                                          -> canceled_at
                                          -> expired_at
                                          -> trouble_at
    """
    CREATED = 'created'              # Создана
    NEED_CREDS = 'creds_at'          # Ожидает назначения реквизитов
    MANUAL_CREDS = 'manual_creds_at' # Ожидает ручного ввода реквизитов
    WAITING = 'waiting_at'           # Ожидает оплаты (реквизиты назначены)
    PAYED = 'payed_at'               # Оплачено клиентом (ожидает подтверждения)
    DONE = 'done_at'                 # Выполнена (баланс пополнен)
    TROUBLE = 'trouble_at'           # Открыт спор
    EXPIRED = 'expired_at'           # Просрочена
    CANCELED = 'canceled_at'         # Отменена

    # Группы статусов для фильтрации
    ACTIVE = [CREATED, NEED_CREDS, MANUAL_CREDS, WAITING, PAYED]
    COMPLETED = [DONE]
    FAILED = [CANCELED, EXPIRED]


class PurchaseStatus:
    """
    Статусы покупок (PurchaseRequest).

    Жизненный цикл:
        1 (created) -> 2 (done)
                    -> 3 (canceled)
                    -> 4 (trouble)
    """
    CREATED = '1'    # Создана
    DONE = '2'       # Выполнена (товар выдан)
    CANCELED = '3'   # Отменена
    TROUBLE = '4'    # Открыт спор
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from .exceptions import (
    MerchantApiError, AuthenticationError, RateLimitError,
    ValidationError, NotFoundError, ServerError, TorConnectionError
)


class WebClientApiClient:
    """
    Клиент для Web Client API - авторизация покупателей на сайте магазина.

    Двухуровневая авторизация:
    - Authorization: Bearer <api_key> - для идентификации магазина (все запросы)
    - X-Client-Session: <token> - для авторизации клиента (защищённые endpoints)

    Args:
        base_url: URL API магазина
        api_key: MerchantApiKey (Bearer token для Authorization header)
        use_tor: Использовать TOR proxy (default: True)
        tor_proxy: URL SOCKS5 proxy для TOR (default: socks5h://127.0.0.1:9050)
        timeout: Таймаут запросов в секундах (default: 30)

    Example:
        >>> client = WebClientApiClient(
        ...     base_url='https://example.onion',
        ...     api_key='your_merchant_api_key'
        ... )
        >>> # Получить captcha
        >>> captcha = client.get_captcha()
        >>> # Регистрация
        >>> result = client.register(captcha['captcha_id'], 'answer123')
        >>> print(result['auth_code'])  # Сохранить для последующего входа!
        >>> # Теперь можно использовать защищённые методы
        >>> profile = client.get_profile()
    """

    DEFAULT_TOR_PROXY = "socks5h://127.0.0.1:9050"

    def __init__(self, base_url: str, api_key: str,
                 use_tor: bool = True, tor_proxy: str = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.use_tor = use_tor
        self.tor_proxy = tor_proxy or self.DEFAULT_TOR_PROXY
        self.timeout = timeout
        self.session_token: Optional[str] = None
        self._session = self._create_session()

    def _create_session(self):
        """Создаёт HTTP сессию с настройками авторизации и proxy."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        if self.use_tor:
            session.proxies = {"http": self.tor_proxy, "https": self.tor_proxy}
        return session

    def _get_headers(self, require_session: bool = False) -> Dict[str, str]:
        """
        Формирует заголовки для запроса.

        Args:
            require_session: Требуется ли клиентская сессия
        """
        headers = {}
        if require_session:
            if not self.session_token:
                raise AuthenticationError("Требуется авторизация. Вызовите login() или register() сначала.")
            headers["X-Client-Session"] = self.session_token
        return headers

    def _request(self, method: str, endpoint: str, params: Dict = None,
                 json_data: Dict = None, require_session: bool = False) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API.

        Args:
            method: HTTP метод (GET, POST)
            endpoint: Путь endpoint (без /api/v1/)
            params: Query параметры
            json_data: JSON тело запроса
            require_session: Требуется ли X-Client-Session header
        """
        url = urljoin(self.base_url, f"/api/v1/{endpoint.lstrip('/')}")
        headers = self._get_headers(require_session)

        try:
            resp = self._session.request(
                method, url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=self.timeout
            )
        except requests.exceptions.ProxyError as e:
            raise TorConnectionError(f"TOR proxy connection failed: {e}")
        except requests.exceptions.RequestException as e:
            raise MerchantApiError(f"Request failed: {e}")

        return self._handle_response(resp)

    def _handle_response(self, resp) -> Dict[str, Any]:
        """Обрабатывает HTTP ответ и возвращает данные или вызывает исключение."""
        try:
            data = resp.json()
        except ValueError:
            data = {"error": resp.text}

        if resp.status_code in (200, 201, 202, 206):
            return data
        elif resp.status_code == 400:
            raise ValidationError(
                data.get("error") or data.get("text") or "Validation error",
                status_code=400,
                response=data,
                error_code=data.get("error_code")
            )
        elif resp.status_code in (401, 403):
            raise AuthenticationError(
                data.get("error") or data.get("text") or "Authentication failed",
                status_code=resp.status_code,
                error_code=data.get("error_code")
            )
        elif resp.status_code == 404:
            raise NotFoundError(
                data.get("error") or data.get("text") or "Not found",
                status_code=404,
                error_code=data.get("error_code")
            )
        elif resp.status_code == 429:
            raise RateLimitError(
                data.get("error") or data.get("text") or "Rate limit exceeded",
                status_code=429,
                retry_after=resp.headers.get("Retry-After")
            )
        elif resp.status_code >= 500:
            raise ServerError(
                data.get("error") or data.get("text") or "Server error",
                status_code=resp.status_code
            )
        raise MerchantApiError(
            data.get("error") or data.get("text") or f"Unknown error (HTTP {resp.status_code})",
            status_code=resp.status_code,
            response=data
        )

    # =========================================================================
    # Установка токена сессии
    # =========================================================================

    def set_session_token(self, token: str):
        """
        Устанавливает токен клиентской сессии.

        Вызывается автоматически после login() и register().
        Можно вызвать вручную если токен уже есть.

        Args:
            token: Токен сессии для X-Client-Session header
        """
        self.session_token = token

    # =========================================================================
    # Публичные endpoints (только api_key)
    # =========================================================================

    def get_captcha(self) -> Dict[str, Any]:
        """
        Получает captcha для регистрации/входа.

        Returns:
            dict: {
                'result': 'success',
                'captcha_id': str,
                'image': str (data:image/png;base64,...)
            }
        """
        return self._request("GET", "client/captcha/")

    def register(self, captcha_id: str, captcha_answer: str) -> Dict[str, Any]:
        """
        Регистрирует нового клиента.

        После успешной регистрации автоматически сохраняет токен сессии.

        Args:
            captcha_id: ID captcha из get_captcha()
            captcha_answer: Ответ на captcha

        Returns:
            dict: {
                'result': 'success',
                'auth_code': str,  # СОХРАНИТЕ ЭТОТ КОД!
                'token': str,
                'message': str
            }
        """
        data = self._request("POST", "client/register/", json_data={
            "captcha_id": captcha_id,
            "captcha_answer": captcha_answer
        })
        if data.get("token"):
            self.session_token = data["token"]
        return data

    def login(self, auth_code: str, captcha_id: str, captcha_answer: str) -> Dict[str, Any]:
        """
        Вход клиента по коду авторизации.

        После успешного входа автоматически сохраняет токен сессии.

        Args:
            auth_code: Код авторизации (слово-число-слово)
            captcha_id: ID captcha из get_captcha()
            captcha_answer: Ответ на captcha

        Returns:
            dict: {
                'result': 'success',
                'token': str,
                'auth_code': str,
                'message': str
            }
        """
        data = self._request("POST", "client/login/", json_data={
            "auth_code": auth_code,
            "captcha_id": captcha_id,
            "captcha_answer": captcha_answer
        })
        if data.get("token"):
            self.session_token = data["token"]
        return data

    # =========================================================================
    # Защищённые endpoints (api_key + session_token)
    # =========================================================================

    def get_profile(self) -> Dict[str, Any]:
        """
        Получает профиль текущего клиента.

        Returns:
            dict: {
                'result': 'success',
                'data': {
                    'pk': int,                           # ID клиента
                    'balance': float,                    # Баланс
                    'currency': str,                     # Код валюты мерчанта
                    'telegram_linked': bool,             # Привязан ли Telegram
                    'uid': str,                          # Telegram UID или web_xxx
                    'username': str,                     # Telegram username
                    'first_name': str,                   # Имя
                    'last_name': str,                    # Фамилия
                    'avatar': str,                       # URL аватара
                    'lang': str,                         # Код языка
                    'discount': float,                   # Общая скидка клиента (%)
                    'is_banned': bool,                   # Забанен
                    'is_banned_for_reviews': bool,       # Бан на отзывы
                    'is_banned_for_promos': bool,        # Бан на промокоды
                    'is_banned_for_lucky': bool,         # Бан на удачу
                    'is_banned_for_casino': bool,        # Бан на казино
                    'is_banned_for_ruletka': bool,       # Бан на рулетку
                    'is_banned_for_privatebot': bool,    # Бан на приватный бот
                    'is_banned_for_support': bool,       # Бан на поддержку
                    'is_banned_for_referal': bool,       # Бан на рефералы
                    'is_banned_for_disputs': bool,       # Бан на споры
                    'web_auth_code': str,                # Код авторизации
                    'web_auth_code_created_at': str,     # Дата создания кода
                    'web_last_login_at': str,            # Последний вход
                    'referals_count': int,               # Количество рефералов
                    'deposit_count': int,                # Количество пополнений
                    'purchase_count': int,               # Количество покупок
                    'doned_purchase_count': int,         # Выполненных покупок
                    'total_spent': float,                # Всего потрачено
                    'trouble_purchase_count': int,       # Споров по покупкам
                    'purchase_promocoded_count': int,    # Покупок с промокодом
                    'returned_purchase_count': int,      # Возвращённых покупок
                    'opened_disput_count': int,          # Открытых споров
                    'last_returned_at': str,             # Последний возврат
                    'changed_count': int,                # Количество обменов
                    'last_changed_at': str,              # Последний обмен
                    'created': str,                      # Дата регистрации
                }
            }
        """
        return self._request("GET", "client/me/", require_session=True)

    def logout(self) -> Dict[str, Any]:
        """
        Выход из системы. Завершает текущую сессию.

        Returns:
            dict: {'result': 'success', 'message': 'Logged out'}
        """
        result = self._request("POST", "client/logout/", require_session=True)
        self.session_token = None
        return result

    def regenerate_auth_code(self) -> Dict[str, Any]:
        """
        Перегенерация кода авторизации.

        Генерирует новый код формата слово-число-слово.
        Можно вызывать не чаще 1 раза в час.

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}

        Raises:
            MerchantApiError: Если прошло менее часа с последней генерации (RATE_LIMIT)
        """
        return self._request("POST", "client/regenerate-code/", require_session=True)

    def get_telegram_link(self) -> Dict[str, Any]:
        """
        Получает ссылку для привязки Telegram аккаунта.

        Returns:
            dict: {
                'result': 'success',
                'link': str,
                'expires_in': int (секунды)
            }
        """
        return self._request("POST", "client/connect-telegram/", require_session=True)

    def get_telegram_status(self) -> Dict[str, Any]:
        """
        Проверяет статус привязки Telegram.

        Returns:
            dict: {
                'result': 'success',
                'linked': bool,
                'telegram_uid': str or None
            }
        """
        return self._request("GET", "client/telegram-status/", require_session=True)

    # =========================================================================
    # Пополнения (Deposits)
    # =========================================================================

    def get_payment_methods(self) -> Dict[str, Any]:
        """
        Получает доступные методы оплаты.

        Returns:
            dict: {
                'result': 'success',
                'data': [{'code': str, 'name': str}, ...],
                'currency': str,
                'min_amount': float,
                'max_amount': float
            }
        """
        return self._request("GET", "client/payment-methods/", require_session=True)

    def get_deposits(self, page: int = None, status: str = None) -> Dict[str, Any]:
        """
        Получает список пополнений клиента.

        Args:
            page: Номер страницы (опционально)
            status: Фильтр по статусу (опционально):
                - 'active' — активные заявки (ожидают оплаты, назначения реквизитов)
                - 'completed' — выполненные заявки
                - 'canceled' — отменённые и просроченные заявки
                - 'dispute' — заявки в споре

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...], 'next': str, 'previous': str}

        Example:
            # Получить все пополнения
            deposits = client.get_deposits()

            # Получить только активные заявки
            active = client.get_deposits(status='active')

            # Получить выполненные заявки с пагинацией
            completed = client.get_deposits(page=2, status='completed')
        """
        params = {}
        if page:
            params["page"] = page
        if status:
            params["status"] = status
        return self._request("GET", "client/deposits/", params=params, require_session=True)

    def get_active_deposit(self) -> Optional[Dict[str, Any]]:
        """
        Получает активную заявку на пополнение (если есть).

        У клиента может быть только одна активная заявка.

        Returns:
            dict или None: Данные активной заявки или None если нет активных заявок

        Example:
            active = client.get_active_deposit()
            if active:
                print(f"Активная заявка #{active['pk']} на сумму {active['amount']}")
            else:
                print("Нет активных заявок")
        """
        result = self.get_deposits(status='active')
        if result.get('data'):
            return result['data'][0]
        return None

    def create_deposit(self, payment_type: str, amount: float) -> Dict[str, Any]:
        """
        Создаёт заявку на пополнение баланса.

        Args:
            payment_type: Тип оплаты (из get_payment_methods())
            amount: Сумма пополнения

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", "client/deposits/create/", json_data={
            "payment_type": payment_type,
            "amount": amount
        }, require_session=True)

    def get_deposit(self, deposit_id: int) -> Dict[str, Any]:
        """
        Получает детали пополнения.

        Args:
            deposit_id: ID пополнения

        Returns:
            dict: {'result': 'success', 'data': {...}}
        """
        return self._request("GET", f"client/deposits/{deposit_id}/", require_session=True)

    def confirm_deposit(self, deposit_id: int) -> Dict[str, Any]:
        """
        Подтверждает оплату пополнения.

        Args:
            deposit_id: ID пополнения

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", f"client/deposits/{deposit_id}/confirm/", require_session=True)

    def cancel_deposit(self, deposit_id: int) -> Dict[str, Any]:
        """
        Отменяет заявку на пополнение.

        Args:
            deposit_id: ID пополнения

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", f"client/deposits/{deposit_id}/cancel/", require_session=True)

    def get_deposit_messages(self, deposit_id: int) -> Dict[str, Any]:
        """
        Получает список сообщений по заявке на пополнение.

        Args:
            deposit_id: ID заявки на пополнение

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}

        Example:
            messages = client.get_deposit_messages(123)
            for msg in messages['data']:
                print(f"[{msg['created']}] {msg['text']}")
        """
        return self._request("GET", f"client/deposits/{deposit_id}/messages/", require_session=True)

    def send_deposit_message(
        self,
        deposit_id: int,
        text: str = None,
    ) -> Dict[str, Any]:
        """
        Отправляет текстовое сообщение по заявке на пополнение.

        Для отправки фото используйте upload_photos(), получите URL,
        затем вставьте URL в текст сообщения.

        Args:
            deposit_id: ID заявки на пополнение
            text: Текст сообщения (обязательно)

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}

        Example:
            # Текстовое сообщение
            client.send_deposit_message(123, text="Оплатил, жду подтверждения")

            # Сообщение с фото (сначала загрузите через upload_photos)
            photos = client.upload_photos(123, 'deposit', ["/path/to/receipt.jpg"])
            url = photos['data'][0]['url']
            client.send_deposit_message(123, text=f"Чек оплаты: {url}")
        """
        if not text:
            raise ValueError("Укажите text")

        return self._request(
            "POST",
            f"client/deposits/{deposit_id}/messages/",
            json_data={'text': text},
            require_session=True
        )

    def open_deposit_dispute(self, deposit_id: int) -> Dict[str, Any]:
        """
        Открывает спор по заявке на пополнение.

        Условия:
        - Заявка должна быть отменена или просрочена
        - С момента отмены прошло не более 3 часов
        - По заявке были назначены реквизиты
        - У клиента нет других открытых споров

        Args:
            deposit_id: ID заявки на пополнение

        Returns:
            dict: {'result': 'success', 'message': 'Dispute opened'}

        Example:
            result = client.open_deposit_dispute(123)
        """
        return self._request(
            "POST",
            f"client/deposits/{deposit_id}/dispute/",
            require_session=True
        )

    # =========================================================================
    # Покупки (Purchases)
    # =========================================================================

    def get_purchases(self, page: int = None, status: str = None) -> Dict[str, Any]:
        """
        Получает список покупок клиента.

        Args:
            page: Номер страницы (опционально)
            status: Фильтр по статусу (опционально):
                    '1' - создан, '2' - выполнен, '3' - отменён, '4' - спор

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}
        """
        params = {}
        if page:
            params["page"] = page
        if status:
            params["status"] = status
        return self._request("GET", "client/purchases/", params=params, require_session=True)

    def create_purchase(self, product_id: int, location_id: int) -> Dict[str, Any]:
        """
        Создаёт покупку товара.

        Средства списываются с баланса клиента.

        Args:
            product_id: ID товара
            location_id: ID локации

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", "client/purchases/create/", json_data={
            "product_id": product_id,
            "location_id": location_id
        }, require_session=True)

    def get_purchase(self, purchase_id: int) -> Dict[str, Any]:
        """
        Получает детали покупки.

        Args:
            purchase_id: ID покупки

        Returns:
            dict: {'result': 'success', 'data': {...}}
        """
        return self._request("GET", f"client/purchases/{purchase_id}/", require_session=True)

    def open_dispute(self, purchase_id: int) -> Dict[str, Any]:
        """
        Открывает спор по покупке.

        Args:
            purchase_id: ID покупки

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", f"client/purchases/{purchase_id}/dispute/", require_session=True)

    def close_dispute(self, purchase_id: int) -> Dict[str, Any]:
        """
        Закрывает спор по покупке (клиент сам отменяет спор).

        Args:
            purchase_id: ID покупки

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", f"client/purchases/{purchase_id}/close-dispute/", require_session=True)

    def get_purchase_messages(self, purchase_id: int) -> Dict[str, Any]:
        """
        Получает список сообщений по покупке.

        Args:
            purchase_id: ID покупки

        Returns:
            dict: {'result': 'success', 'data': [...]}

        Example:
            >>> messages = client.get_purchase_messages(123)
            >>> for msg in messages['data']:
            ...     print(f"{msg['created']}: {msg['text']}")
        """
        return self._request("GET", f"client/purchases/{purchase_id}/messages/", require_session=True)

    def send_purchase_message(
        self,
        purchase_id: int,
        text: str = None,
    ) -> Dict[str, Any]:
        """
        Отправляет текстовое сообщение по покупке (в споре).

        Для отправки фото используйте upload_photos(), получите URL,
        затем вставьте URL в текст сообщения.

        Args:
            purchase_id: ID покупки
            text: Текст сообщения (обязательно)

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}

        Example:
            >>> # Отправить текстовое сообщение
            >>> client.send_purchase_message(123, text='Проблема с товаром')
            >>>
            >>> # Сообщение с фото (сначала загрузите через upload_photos)
            >>> photos = client.upload_photos(123, 'purchase', ['/path/to/photo.jpg'])
            >>> url = photos['data'][0]['url']
            >>> client.send_purchase_message(123, text=f'Фото проблемы: {url}')
        """
        if not text:
            raise ValueError("Укажите text")

        return self._request(
            "POST",
            f"client/purchases/{purchase_id}/messages/",
            json_data={'text': text},
            require_session=True
        )

    # =========================================================================
    # Отзывы (Reviews)
    # =========================================================================

    def get_reviews(self, page: int = None) -> Dict[str, Any]:
        """
        Получает список отзывов клиента.

        Args:
            page: Номер страницы (опционально)

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}
        """
        params = {}
        if page:
            params["page"] = page
        return self._request("GET", "client/reviews/", params=params, require_session=True)

    def create_review(self, purchase_id: int, rate: int, text: str) -> Dict[str, Any]:
        """
        Создаёт отзыв по покупке.

        Ограничения:
        - Покупка должна быть завершена (статус "Выполнена")
        - Отзыв можно оставить не позднее 1 дня после завершения покупки
        - Можно оставить только один отзыв на покупку
        - Клиент не должен быть забанен для отзывов
        - Текст отзыва минимум 5 символов
        - Текст не должен повторять другие отзывы
        - Оценка от 1 до 5

        Args:
            purchase_id: ID покупки
            rate: Оценка от 1 до 5
            text: Текст отзыва (минимум 5 символов)

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': '...'}

        Raises:
            ApiError: При ошибке валидации или если отзыв уже существует

        Example:
            >>> review = client.create_review(123, 5, 'Отличный товар, рекомендую!')
            >>> print(review['data']['pk'])
        """
        return self._request(
            "POST",
            "client/reviews/",
            json_data={
                "purchase_id": purchase_id,
                "rate": rate,
                "text": text
            },
            require_session=True
        )

    # =========================================================================
    # Поддержка (Support)
    # =========================================================================

    def get_support_messages(self, page: int = None) -> Dict[str, Any]:
        """
        Получает историю переписки с поддержкой.

        Args:
            page: Номер страницы (опционально)

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}
        """
        params = {}
        if page:
            params["page"] = page
        return self._request("GET", "client/support/", params=params, require_session=True)

    def send_support_message(self, text: str) -> Dict[str, Any]:
        """
        Отправляет сообщение в поддержку.

        Args:
            text: Текст сообщения (max 4096 символов)

        Returns:
            dict: {'result': 'success', 'data': {...}, 'message': str}
        """
        return self._request("POST", "client/support/create/", json_data={
            "text": text
        }, require_session=True)

    # =========================================================================
    # Промокоды (Promocodes)
    # =========================================================================

    def get_promocodes(self, page: int = None) -> Dict[str, Any]:
        """
        Получает историю активированных промокодов (старый и новый формат).

        Возвращает объединённый список промокодов из обоих форматов хранения,
        отсортированный по дате активации (новые сверху).

        Args:
            page: Номер страницы (опционально)

        Returns:
            dict: {
                'result': 'success',
                'count': int,
                'next': str | None,
                'previous': str | None,
                'data': [
                    {
                        'code': str,         # Маскированный код (первые 6 + *** + последние 3)
                        'amount': int,       # Номинал промокода
                        'activated_at': str  # Дата активации ISO 8601
                    },
                    ...
                ]
            }
        """
        params = {}
        if page:
            params["page"] = page
        return self._request("GET", "client/promocodes/", params=params, require_session=True)

    def activate_promocode(self, code: str) -> Dict[str, Any]:
        """
        Активирует промокод.

        Args:
            code: Код промокода

        Returns:
            dict: {'result': 'success', 'message': str, 'new_balance': float}
        """
        return self._request("POST", "client/promocodes/activate/", json_data={
            "code": code
        }, require_session=True)

    # =========================================================================
    # Подписки, розыгрыши, скидки
    # =========================================================================

    def get_subscriptions(self, page: int = None) -> Dict[str, Any]:
        """
        Получает список подписок на каналы.

        Args:
            page: Номер страницы (опционально)

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}
        """
        params = {}
        if page:
            params["page"] = page
        return self._request("GET", "client/subscriptions/", params=params, require_session=True)

    def get_lottery(self, page: int = None) -> Dict[str, Any]:
        """
        Получает историю участия в розыгрышах.

        Args:
            page: Номер страницы (опционально)

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}
        """
        params = {}
        if page:
            params["page"] = page
        return self._request("GET", "client/lottery/", params=params, require_session=True)

    def get_discounts(self, page: int = None, active: bool = None) -> Dict[str, Any]:
        """
        Получает персональные скидки клиента.

        Args:
            page: Номер страницы (опционально)
            active: True - только активные (неиспользованные), None/не указан - все

        Returns:
            dict: {'result': 'success', 'count': int, 'data': [...]}
        """
        params = {}
        if page:
            params["page"] = page
        if active is not None:
            params["active"] = str(active).lower()
        return self._request("GET", "client/discounts/", params=params, require_session=True)

    # =========================================================================
    # TOR utilities
    # =========================================================================

    def check_tor_connection(self) -> bool:
        """
        Проверяет работу TOR соединения.

        Returns:
            bool: True если соединение через TOR работает
        """
        if not self.use_tor:
            return False
        try:
            resp = self._session.get("https://check.torproject.org/api/ip", timeout=10)
            return resp.json().get("IsTor", False)
        except:
            return False

    def set_tor(self, enabled: bool, proxy: str = None):
        """
        Включает/выключает TOR proxy.

        Args:
            enabled: Включить TOR
            proxy: URL SOCKS5 proxy (опционально)
        """
        self.use_tor = enabled
        if proxy:
            self.tor_proxy = proxy
        self._session = self._create_session()
