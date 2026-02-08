"""
Модели базы данных LUCICORE.

Определяет SQLAlchemy-модели для всех таблиц.
Каждая сущность получает уникальный ``hash_id`` — публичный
идентификатор, используемый вместо числового ``id`` в API.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, event
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """Модель пользователя.

    Содержит профильные данные, статус, баланс,
    интеграцию с Merchant API и привязку к Telegram.

    Атрибуты:
        id:                  Внутренний числовой PK (не отдаётся наружу).
        hash_id:             Уникальный публичный HASH-идентификатор (22 символа).
        username:            Уникальное имя пользователя.
        email:               E-mail (уникальный, опционально).
        password_hash:       Хеш пароля (PBKDF2-SHA256).
        first_name:          Имя.
        last_name:           Фамилия.
        avatar:              URL аватара.
        is_active:           Активен ли аккаунт.
        is_verified:         Подтверждён ли аккаунт.
        balance:             Баланс пользователя.
        merchant_client_id:  ID клиента в Merchant API.
        telegram_uid:        UID в Telegram.
        session_token:       Сессионный токен Merchant API.
        created_at:          Дата создания.
        updated_at:          Дата последнего обновления.
        last_login:          Дата последнего входа.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    hash_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Поля профиля
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    avatar = Column(String(500), nullable=True)

    # Флаги статуса
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Баланс (из функции баланса клиента Merchant API)
    balance = Column(Float, default=0.0)

    # Поля интеграции с Merchant API
    merchant_client_id = Column(Integer, nullable=True, index=True)
    telegram_uid = Column(String(255), nullable=True, unique=True)
    session_token = Column(String(500), nullable=True)

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User(hash_id={self.hash_id!r}, username={self.username!r})>"


def _set_hash_id_before_insert(mapper, connection, target):
    """Автоматически генерирует ``hash_id`` перед INSERT, если не задан."""
    if not target.hash_id:
        from app.security import generate_hash_id
        target.hash_id = generate_hash_id()


# Подписка на событие — hash_id генерируется автоматически при создании
event.listen(User, "before_insert", _set_hash_id_before_insert)
