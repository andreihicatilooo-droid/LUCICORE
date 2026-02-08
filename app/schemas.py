"""
Pydantic-схемы валидации LUCICORE API.

Определяет модели для входных и выходных данных всех эндпоинтов.
Публичные ответы содержат ``hash_id`` вместо числового ``id``.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Схемы пользователя
# ---------------------------------------------------------------------------

class UserDatabase(BaseModel):
    """Полная схема пользователя в базе данных (внутреннее использование).

    Включает числовой ``id`` — используется ТОЛЬКО внутри сервера.
    """
    id: int
    hash_id: str
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_verified: bool
    balance: float
    merchant_client_id: Optional[int] = None
    telegram_uid: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Базовая схема пользователя (общие поля).

    Атрибуты:
        username:   Уникальное имя пользователя.
        email:      E-mail (опционально).
        first_name: Имя.
        last_name:  Фамилия.
        avatar:     URL аватара.
    """
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(UserBase):
    """Схема создания пользователя.

    Атрибуты:
        password: Пароль в открытом виде (будет захеширован на сервере).
    """
    password: str


class UserUpdate(BaseModel):
    """Схема обновления пользователя.

    Все поля опциональны — передаются только изменяемые.
    """
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserLogin(BaseModel):
    """Схема входа пользователя.

    Атрибуты:
        username: Имя пользователя.
        password: Пароль в открытом виде.
    """
    username: str
    password: str


class UserBalanceUpdate(BaseModel):
    """Схема обновления баланса пользователя.

    Атрибуты:
        amount:    Сумма операции.
        operation: Тип операции — ``"add"`` (пополнение) или ``"subtract"`` (списание).
    """
    amount: float
    operation: str = "add"  # "add" или "subtract"


# ---------------------------------------------------------------------------
# Схемы Merchant API / Web Client API
# ---------------------------------------------------------------------------

class MerchantCaptcha(BaseModel):
    """Данные капчи Web Client API.

    Атрибуты:
        captcha_id: Идентификатор капчи.
        image:      Base64-изображение капчи.
    """
    captcha_id: str
    image: str


class MerchantLinkRequest(BaseModel):
    """Запрос на привязку пользователя к Web Client API.

    Атрибуты:
        captcha_id:     Идентификатор капчи.
        captcha_answer: Ответ на капчу.
    """
    captcha_id: str
    captcha_answer: str


class MerchantLoginRequest(BaseModel):
    """Запрос на вход через Web Client API.

    Атрибуты:
        auth_code:      Код авторизации.
        captcha_id:     Идентификатор капчи.
        captcha_answer: Ответ на капчу.
    """
    auth_code: str
    captcha_id: str
    captcha_answer: str


class MerchantLinkResponse(BaseModel):
    """Ответ после привязки пользователя к Web Client API.

    Атрибуты:
        hash_id:            Публичный HASH-идентификатор пользователя.
        merchant_client_id: ID клиента в Merchant API.
        auth_code:          Код авторизации для дальнейших операций.
    """
    hash_id: str
    merchant_client_id: int
    auth_code: str


class User(UserBase):
    """Публичная схема ответа пользователя.

    Содержит ``hash_id`` вместо числового ``id`` — это публичный
    уникальный идентификатор, безопасный для передачи клиенту.

    Атрибуты:
        hash_id:            Уникальный HASH-идентификатор (22 символа).
        is_active:          Активен ли аккаунт.
        is_verified:        Подтверждён ли аккаунт.
        balance:            Баланс пользователя.
        merchant_client_id: ID клиента в Merchant API.
        telegram_uid:       UID в Telegram.
        created_at:         Дата создания.
        updated_at:         Дата последнего обновления.
        last_login:         Дата последнего входа.
    """
    hash_id: str
    is_active: bool
    is_verified: bool
    balance: float
    merchant_client_id: Optional[int] = None
    telegram_uid: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
