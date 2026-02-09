"""
Pydantic-схемы валидации LUCICORE API.

Определяет модели для входных и выходных данных всех эндпоинтов.
Публичные ответы содержат ``hash_id`` (UUID v4) вместо числового ``id``.

Структура файла:
    • Схемы пользователя        — UserDatabase, UserBase, UserCreate, UserUpdate, …
    • Схемы Merchant / Web Client — MerchantCaptcha, MerchantLinkRequest, …
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# Схемы пользователя
# ═══════════════════════════════════════════════════════════════════════════

class UserDatabase(BaseModel):
    """Полная схема пользователя в базе данных (внутреннее использование).

    Включает числовой ``id`` — используется ТОЛЬКО внутри сервера.
    Все поля соответствуют прямым атрибутам и прокси-свойствам ``models.User``.
    """
    id: int
    hash_id: str
    login: str
    username: str
    status: str
    astatus: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    balance: float
    merchant_client_id: Optional[int] = None
    telegram_uid: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Базовая схема пользователя (общие поля для создания и ответа).

    Атрибуты:
        login:        Уникальное имя для входа.
        username:     Уникальное отображаемое имя.
        display_name: Альтернативное отображаемое имя (опционально).
        email:        E-mail (опционально).
        avatar:       URL аватара (опционально).
    """
    login: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(UserBase):
    """Схема создания пользователя.

    Обязательные поля: ``login``, ``username``, ``password``.
    Остальные (``email``, ``display_name``, ``avatar``) — опциональны.

    Атрибуты:
        password: Пароль в открытом виде (будет захеширован на сервере).
    """
    password: str


class UserUpdate(BaseModel):
    """Схема обновления пользователя.

    Все поля опциональны — передаются только изменяемые.

    Атрибуты:
        login:        Новый логин.
        username:     Новое имя пользователя.
        status:       Статус аккаунта (active, blocked, …).
        astatus:      Статус администратора (lord, demon, imp, none).
        display_name: Отображаемое имя.
        email:        E-mail.
        avatar:       URL аватара.
    """
    login: Optional[str] = None
    username: Optional[str] = None
    status: Optional[str] = None
    astatus: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


class UserLogin(BaseModel):
    """Схема входа пользователя.

    Атрибуты:
        login:    Логин пользователя.
        password: Пароль в открытом виде.
    """
    login: str
    password: str


class UserBalanceUpdate(BaseModel):
    """Схема обновления баланса пользователя.

    Атрибуты:
        amount:    Сумма операции.
        operation: Тип операции — ``"add"`` (пополнение) или ``"subtract"`` (списание).
    """
    amount: float
    operation: str = "add"  # "add" или "subtract"


# ═══════════════════════════════════════════════════════════════════════════
# Схемы Merchant API / Web Client API
# ═══════════════════════════════════════════════════════════════════════════

class MerchantCaptcha(BaseModel):
    """Данные капчи Web Client API.

    Атрибуты:
        captcha_id: Идентификатор капчи.
        image:      Base64-изображение капчи (data:image/png;base64,…).
        image_url:  Прямая ссылка на PNG-файл капчи на сервере.
    """
    captcha_id: str
    image: str
    image_url: str


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
        hash_id:            Публичный UUID v4 идентификатор пользователя.
        merchant_client_id: ID клиента в Merchant API.
        auth_code:          Код авторизации для дальнейших операций.
    """
    hash_id: str
    merchant_client_id: int
    auth_code: str


class User(UserBase):
    """Публичная схема ответа пользователя.

    Содержит ``hash_id`` (UUID v4) вместо числового ``id`` — это публичный
    уникальный идентификатор, безопасный для передачи клиенту.

    Атрибуты:
        hash_id:            UUID v4 идентификатор (36 символов).
        status:             Статус аккаунта.
        astatus:            Статус администратора.
        balance:            Баланс пользователя.
        merchant_client_id: ID клиента в Merchant API.
        telegram_uid:       UID в Telegram.
        created_at:         Дата создания.
        updated_at:         Дата последнего обновления.
        last_login:         Дата последнего входа.
    """
    hash_id: str
    status: str
    astatus: str
    balance: float
    merchant_client_id: Optional[int] = None
    telegram_uid: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
