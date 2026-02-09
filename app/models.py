"""
Модели базы данных LUCICORE.

Определяет SQLAlchemy-модели для всех таблиц.
Каждая сущность получает уникальный ``hash_id`` — публичный
идентификатор, используемый вместо числового ``id`` в API.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, event, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

USER_STATUS_ACTIVE = "active"
USER_STATUS_LOGGED_OUT = "logged_out"
USER_STATUS_ON_REVIEW = "on_review"
USER_STATUS_BLOCKED = "blocked"
USER_STATUS_DELETED = "deleted"


class User(Base):
    """Модель пользователя.

    Содержит только основную информацию о пользователе и его статусе.

    Атрибуты:
        id:                  Внутренний числовой PK (не отдаётся наружу).
        hash_id:             UUID v4. Как строка (универсально).
        login:               Логин (уникальный). мин 5 макс 15 символов.
        username:            Уникальное имя пользователя (мин 5 макс 20 символов).
        display_name:        Отображаемое имя (необязательно, мин 3 макс 30 символов).

        password_hash:       Хеш пароля (PBKDF2-SHA256).
        status:              Статус аккаунта.
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
    status = Column(String(32), nullable=False, default=USER_STATUS_ACTIVE, index=True)

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

    settings = relationship(
        "UserSetting",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    msdk = relationship(
        "UserMSDK",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tg = relationship(
        "UserTG",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    stats = relationship(
        "UserStats",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reputation = relationship(
        "UserReputation",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def _ensure_settings(self):
        if self.settings is None:
            self.settings = UserSetting()
        return self.settings

    def _ensure_msdk(self):
        if self.msdk is None:
            self.msdk = UserMSDK()
        return self.msdk

    def _ensure_tg(self):
        if self.tg is None:
            self.tg = UserTG()
        return self.tg

    @property
    def display_name(self):
        return self.settings.display_name if self.settings else None

    @display_name.setter
    def display_name(self, value):
        self._ensure_settings().display_name = value

    @property
    def email(self):
        return self.settings.email if self.settings else None

    @email.setter
    def email(self, value):
        self._ensure_settings().email = value

    @property
    def avatar(self):
        return self.settings.avatar if self.settings else None

    @avatar.setter
    def avatar(self, value):
        self._ensure_settings().avatar = value

    @property
    def first_name(self):
        return self.settings.first_name if self.settings else None

    @first_name.setter
    def first_name(self, value):
        self._ensure_settings().first_name = value

    @property
    def last_name(self):
        return self.settings.last_name if self.settings else None

    @last_name.setter
    def last_name(self, value):
        self._ensure_settings().last_name = value

    @property
    def merchant_client_id(self):
        return self.msdk.merchant_client_id if self.msdk else None

    @merchant_client_id.setter
    def merchant_client_id(self, value):
        self._ensure_msdk().merchant_client_id = value

    @property
    def balance(self):
        if not self.msdk or self.msdk.balance is None:
            return 0.0
        return self.msdk.balance

    @balance.setter
    def balance(self, value):
        self._ensure_msdk().balance = value

    @property
    def session_token(self):
        return self.msdk.session_token if self.msdk else None

    @session_token.setter
    def session_token(self, value):
        self._ensure_msdk().session_token = value

    @property
    def telegram_uid(self):
        return self.tg.telegram_uid if self.tg else None

    @telegram_uid.setter
    def telegram_uid(self, value):
        self._ensure_tg().telegram_uid = value

    def __repr__(self) -> str:
        return f"<User(hash_id={self.hash_id!r}, username={self.username!r})>"


def _set_hash_id_before_insert(mapper, connection, target):
    """Автоматически генерирует ``hash_id`` перед INSERT, если не задан."""
    if not target.hash_id:
        from app.security import generate_hash_id
        target.hash_id = generate_hash_id()


# Подписка на событие — hash_id генерируется автоматически при создании
event.listen(User, "before_insert", _set_hash_id_before_insert)
