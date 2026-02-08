"""
Merchant API SDK for Python
Supports TOR proxy for enhanced privacy (recommended).

Usage:
    from merchant_api import MerchantApiClient, WebClientApiClient

    # Merchant API - для интеграций мерчантов
    merchant_client = MerchantApiClient(
        base_url="https://your-api-domain.com",
        api_key="your-api-key",
        api_secret="your-api-secret",
        use_tor=True  # Default
    )

    # Web Client API - для авторизации покупателей на сайте
    web_client = WebClientApiClient(
        base_url="https://your-api-domain.com",
        api_key="your-api-key",
        use_tor=True
    )
"""

from .client import MerchantApiClient
from .web_client import WebClientApiClient
from .exceptions import (
    MerchantApiError, AuthenticationError, RateLimitError,
    ValidationError, NotFoundError, ServerError, TorConnectionError
)
from .webhook import WebhookHandler


# Invoice/Deposit Request Status Constants
class InvoiceStatus:
    """Статусы заявки на депозит"""
    CREATED = 'created'              # Заявка создана
    WAITING_CREDS = 'creds_at'       # Ожидает назначения реквизитов
    MANUAL_CREDS = 'manual_creds_at' # Ожидает ручного ввода реквизитов
    WAITING_PAYMENT = 'waiting_at'   # Ожидает оплаты (реквизиты назначены)
    PAID = 'payed_at'                # Оплачено клиентом
    DONE = 'done_at'                 # Выполнена успешно
    TROUBLE = 'trouble_at'           # Проблемная
    EXPIRED = 'expired_at'           # Просрочена
    CANCELED = 'canceled_at'         # Отменена


# Webhook Result Constants
class WebhookResult:
    """Результаты webhook-уведомлений"""
    SUCCESS = 'success'    # Реквизиты успешно назначены
    ERROR = 'error'        # Не удалось назначить реквизиты
    CANCELED = 'canceled'  # Заявка отменена
    EXPIRED = 'expired'    # Заявка просрочена


__version__ = "1.11.1"
__all__ = [
    "MerchantApiClient", "WebClientApiClient", "WebhookHandler",
    "MerchantApiError", "AuthenticationError", "RateLimitError",
    "ValidationError", "NotFoundError", "ServerError", "TorConnectionError",
    "InvoiceStatus", "WebhookResult"
]
