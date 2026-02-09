"""
Модели базы данных LUCICORE.

Определяет SQLAlchemy-модели для всех таблиц.
Каждая сущность получает уникальный ``hash_id`` — публичный
идентификатор, используемый вместо числового ``id`` в API.

Структура файла (блоки):
    0. Импорты и константы
    1. Ядро пользователя     — User
    2. Профиль и настройки    — UserSetting
    3. Интеграции             — UserMSDK, UserTG
    4. Роли и ранги           — UserRole, UserRanksConfig
    5. Репутация и статистика  — UserReputation, UserMessageLog
    6. История и логи          — (TODO) логи паролей, входов, действий
    7. События SQLAlchemy
"""
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Numeric, event, ForeignKey, Boolean, Enum as SqlEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# ═══════════════════════════════════════════════════════════════════════════
# 0. КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════════════════

# --- Статусы аккаунта пользователя ---
USER_STATUS_ACTIVE = "active"
USER_STATUS_LOGGED_OUT = "logged_out"
USER_STATUS_ON_REVIEW = "on_review"
USER_STATUS_BLOCKED = "blocked"
USER_STATUS_DELETED = "deleted"

# --- Статусы администратора ---
ADMIN_STATUS_LORD = "lord"
ADMIN_STATUS_DEMON = "demon"
ADMIN_STATS_IMP = "imp"
ADMIN_STATUS_NONE = "none"


# ═══════════════════════════════════════════════════════════════════════════
# 1. ЯДРО ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════════════════════════════

class User(Base):
    """Модель пользователя.

    Содержит только основную информацию о пользователе и его статусе.

    Атрибуты:
        id:                  Внутренний числовой PK (не отдаётся наружу).
        hash_id:             UUID v4. Как строка (универсально).
        login:               Уникальное имя для входа.
        username:            Уникальное отображаемое имя.
        password_hash:       Хеш пароля (PBKDF2-SHA256).
        status:              Статус аккаунта.
        astatus:             Статус администратора (для админов).
        created_at:          Дата создания.
        updated_at:          Дата последнего обновления.
        last_login:          Дата последнего входа.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    hash_id = Column(String(36), unique=True, nullable=False, index=True)
    login = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default=USER_STATUS_ACTIVE, index=True)
    astatus = Column(String(32), nullable=False, default=ADMIN_STATUS_NONE, index=True)

    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # --- Связи: профиль и настройки (блок 2) ---
    settings = relationship(
        "UserSetting",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # --- Связи: интеграции (блок 3) ---
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

    # --- Связи: роли и ранги (блок 4) ---
    roles = relationship(
        "UserRole",
        foreign_keys="[UserRole.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # --- Связи: репутация и статистика (блок 5) ---
    message_stats = relationship(
        "UserMessageLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reputation = relationship(
        "UserReputation",
        foreign_keys="[UserReputation.target_id]",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    # --- Связи: история и логи (блок 6) — TODO ---

    # ----- Хелперы для ленивой инициализации связей -----

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

    # ----- Прокси-свойства: профиль (блок 2) -----

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

    # ----- Прокси-свойства: Merchant API (блок 3) -----

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

    # ----- Прокси-свойства: Telegram (блок 3) -----

    @property
    def telegram_uid(self):
        return self.tg.telegram_uid if self.tg else None

    @telegram_uid.setter
    def telegram_uid(self, value):
        self._ensure_tg().telegram_uid = value

    def __repr__(self) -> str:
        return f"<User(hash_id={self.hash_id!r}, username={self.username!r})>"


# ═══════════════════════════════════════════════════════════════════════════
# 2. ПРОФИЛЬ И НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════════════════

class UserSetting(Base):
    """Настройки и дополнительные данные профиля пользователя.

    Атрибуты:
        display_name:  Отображаемое имя (необязательно).
        email:         E-mail (уникальный, необязательно).
        avatar:        URL аватара.
        data_json:     Дополнительные данные в формате JSONB (для гибкости).
    """
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    avatar = Column(String(500), nullable=True)
    data_json = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSetting(user_id={self.user_id!r}, display_name={self.display_name!r})>"


# ═══════════════════════════════════════════════════════════════════════════
# 3. ИНТЕГРАЦИИ (Merchant API, Telegram)
# ═══════════════════════════════════════════════════════════════════════════

class UserMSDK(Base):
    """Данные интеграции пользователя с Merchant API.

    Атрибуты:
        merchant_client_id:  ID клиента в Merchant API.
        balance:             Баланс (Numeric для точности).
        session_token:       Сессионный токен Merchant API.
    """
    __tablename__ = "user_msdk"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    merchant_client_id = Column(Integer, nullable=True, index=True)
    balance = Column(Numeric(precision=18, scale=8), nullable=False, default=0)
    session_token = Column(String(500), nullable=True)

    user = relationship("User", back_populates="msdk")

    def __repr__(self) -> str:
        return f"<UserMSDK(user_id={self.user_id!r}, balance={self.balance!r})>"


class UserTG(Base):
    """Данные интеграции пользователя с Telegram.

    Атрибуты:
        telegram_uid:  UID пользователя в Telegram.
        first_name:    Имя из Telegram-профиля.
        last_name:     Фамилия из Telegram-профиля.
        username:      @Никнейм из Telegram-профиля.
    """
    __tablename__ = "user_tg"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    telegram_uid = Column(String(255), nullable=True, unique=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)

    user = relationship("User", back_populates="tg")

    def __repr__(self) -> str:
        return f"<UserTG(user_id={self.user_id!r}, telegram_uid={self.telegram_uid!r})>"


# ═══════════════════════════════════════════════════════════════════════════
# 4. РОЛИ И РАНГИ
# ═══════════════════════════════════════════════════════════════════════════


class UserRole(Base):
    """Связь пользователя с ролью (many-to-many).

    У одного пользователя может быть несколько ролей одновременно
    (например buyer + seller).  Уникальность пары (user_id, role)
    гарантирует UniqueConstraint.

    Атрибуты:
        user_id:      FK → users.
        role:         Роль (enum: user, buyer, seller, servicer, admin).
        assigned_at:  Когда роль была назначена.
        assigned_by:  Кто назначил (FK → users, NULL = система).
    """
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_user_role"),
    )

    class RoleEnum(str, Enum):
        user = "user"
        buyer = "buyer"
        seller = "seller"
        servicer = "servicer"
        admin = "admin"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SqlEnum(RoleEnum, name="user_role_type"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="roles")
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id!r}, role={self.role!r})>"


# TODO: РАЗОБРАТЬСЯ И СОЗДАТЬ РАНГИ
class UserRanksConfig(Base):
    """Справочник рангов пользователей.

    Каждая запись — один ранг для конкретной роли.
    Текущий ранг пользователя определяется как максимальный
    ``rank_level``, где ``min_exp <= user.exp``.

    Атрибуты:
        role:           К какой роли относится ранг.
        rank_level:     Числовой уровень (1, 2, 3…).
        rank_name:      Название (Bronze, Silver, Gold…).
        min_exp:        Минимальный опыт для получения ранга.
        benefits_json:  Бонусы в формате JSONB.
    """
    __tablename__ = "user_ranks_config"

    class Role(str, Enum):
        user = "user"
        buyer = "buyer"
        seller = "seller"
        servicer = "servicer"
        admin = "admin"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SqlEnum(Role, name="user_rank_role"), nullable=False, index=True)
    rank_level = Column(Integer, nullable=False, index=True)
    rank_name = Column(String(255), nullable=False, unique=True)
    min_exp = Column(Integer, nullable=False)
    benefits_json = Column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<UserRanksConfig(role={self.role!r}, rank_name={self.rank_name!r}, level={self.rank_level!r})>"


# ═══════════════════════════════════════════════════════════════════════════
# 5. РЕПУТАЦИЯ И СТАТИСТИКА
# ═══════════════════════════════════════════════════════════════════════════


class UserReputation(Base):
    """Запись об изменении репутации пользователя.

    Каждая строка — одно событие: кто-то (source) изменил репутацию
    кого-то (target) на ``value_change`` единиц с комментарием.

    Атрибуты:
        target_id:     ID пользователя, чья репутация меняется (FK → users).
        source_id:     ID пользователя-инициатора (FK → users, NULL для системы).
        value_change:  Дельта репутации (+1, −1, +5 и т.д.).
        comment:       Комментарий / причина изменения.
        created_at:    Дата и время события.
    """
    __tablename__ = "user_reputation"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    value_change = Column(Integer, nullable=False)
    comment = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    target = relationship("User", foreign_keys=[target_id], back_populates="reputation")
    source = relationship("User", foreign_keys=[source_id])

    def __repr__(self) -> str:
        return (
            f"<UserReputation(target={self.target_id!r}, source={self.source_id!r}, "
            f"change={self.value_change!r})>"
        )


class UserMessageLog(Base):
    """Лог сообщений пользователя.

    Каждая строка — одно сообщение.  Для получения статистики
    за произвольный период используется фильтрация по ``created_at``:

    Примеры SQL::

        -- Всего сообщений
        SELECT COUNT(*) FROM user_message_log WHERE user_id = :uid;

        -- За последний час
        SELECT COUNT(*) FROM user_message_log
         WHERE user_id = :uid AND created_at >= NOW() - INTERVAL '1 hour';

        -- За 1 день / 3 дня / неделю — аналогично с '1 day', '3 days', '7 days'.

    Атрибуты:
        user_id:     FK → users.
        channel:     Канал сообщения (например: 'telegram', 'web', 'api').
        created_at:  Время отправки (индексировано для быстрых агрегатов).
    """
    __tablename__ = "user_message_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(32), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="message_stats")

    def __repr__(self) -> str:
        return f"<UserMessageLog(user_id={self.user_id!r}, channel={self.channel!r}, at={self.created_at!r})>"


# ═══════════════════════════════════════════════════════════════════════════
# 6. ИСТОРИЯ И ЛОГИ
# ═══════════════════════════════════════════════════════════════════════════

# TODO: Логи смены паролей
# TODO: История входов / авторизаций в Telegram
# TODO: Журнал действий пользователя (audit log)


# ═══════════════════════════════════════════════════════════════════════════
# 7. СОБЫТИЯ SQLAlchemy
# ═══════════════════════════════════════════════════════════════════════════

def _set_hash_id_before_insert(mapper, connection, target):
    """Автоматически генерирует ``hash_id`` перед INSERT, если не задан."""
    if not target.hash_id:
        from app.security import generate_hash_id
        target.hash_id = generate_hash_id()


# Подписка на событие — hash_id генерируется автоматически при создании
event.listen(User, "before_insert", _set_hash_id_before_insert)
