"""
CRUD-операции для базы данных LUCICORE.

Содержит функции создания, чтения, обновления и удаления
пользователей.  Поиск возможен по числовому ``id``, ``hash_id``,
``username``, ``email``, ``merchant_client_id`` и ``telegram_uid``.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas


# =========================================================================
# Пользователи — чтение
# =========================================================================

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Получить пользователя по числовому ID (внутренний).

    Аргументы:
        db:      Сессия базы данных.
        user_id: Числовой первичный ключ.

    Возвращает:
        Объект ``User`` или ``None``.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_hash_id(db: Session, hash_id: str) -> Optional[models.User]:
    """Получить пользователя по публичному HASH-идентификатору.

    Это основной способ поиска пользователя в публичных API-запросах.

    Аргументы:
        db:      Сессия базы данных.
        hash_id: Уникальный HASH-идентификатор (22 символа).

    Возвращает:
        Объект ``User`` или ``None``.
    """
    return db.query(models.User).filter(models.User.hash_id == hash_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Получить пользователя по имени пользователя.

    Аргументы:
        db:       Сессия базы данных.
        username: Уникальное имя пользователя.

    Возвращает:
        Объект ``User`` или ``None``.
    """
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Получить пользователя по e-mail.

    Аргументы:
        db:    Сессия базы данных.
        email: E-mail адрес.

    Возвращает:
        Объект ``User`` или ``None``.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_merchant_client_id(db: Session, merchant_client_id: int) -> Optional[models.User]:
    """Получить пользователя по ID клиента Merchant API.

    Аргументы:
        db:                 Сессия базы данных.
        merchant_client_id: ID клиента в Merchant API.

    Возвращает:
        Объект ``User`` или ``None``.
    """
    return db.query(models.User).filter(models.User.merchant_client_id == merchant_client_id).first()


def get_user_by_telegram_uid(db: Session, telegram_uid: str) -> Optional[models.User]:
    """Получить пользователя по Telegram UID.

    Аргументы:
        db:           Сессия базы данных.
        telegram_uid: Уникальный идентификатор Telegram.

    Возвращает:
        Объект ``User`` или ``None``.
    """
    return db.query(models.User).filter(models.User.telegram_uid == telegram_uid).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Получить список пользователей с пагинацией.

    Аргументы:
        db:    Сессия базы данных.
        skip:  Количество пропускаемых записей (по умолчанию 0).
        limit: Максимальное количество записей (по умолчанию 100).

    Возвращает:
        Список объектов ``User``.
    """
    return db.query(models.User).offset(skip).limit(limit).all()


# =========================================================================
# Пользователи — создание
# =========================================================================

def create_user(db: Session, user: schemas.UserCreate, password_hash: str) -> models.User:
    """Создать нового пользователя.

    ``hash_id`` генерируется автоматически через SQLAlchemy-событие
    ``before_insert`` (см. ``models.py``).

    Аргументы:
        db:            Сессия базы данных.
        user:          Данные для создания (схема ``UserCreate``).
        password_hash: Хеш пароля (результат ``security.hash_password``).

    Возвращает:
        Созданный объект ``User`` с заполненным ``hash_id``.
    """
    user_data = user.model_dump(exclude={"password"})
    db_user = models.User(**user_data, password_hash=password_hash)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# =========================================================================
# Пользователи — обновление
# =========================================================================

def update_user(db: Session, user_id: int, user: schemas.UserUpdate) -> Optional[models.User]:
    """Обновить данные пользователя.

    Аргументы:
        db:      Сессия базы данных.
        user_id: Числовой ID пользователя.
        user:    Данные для обновления (схема ``UserUpdate``).

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    update_data = user.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_by_hash(db: Session, hash_id: str, user: schemas.UserUpdate) -> Optional[models.User]:
    """Обновить данные пользователя по HASH-идентификатору.

    Аргументы:
        db:      Сессия базы данных.
        hash_id: Публичный HASH-идентификатор.
        user:    Данные для обновления (схема ``UserUpdate``).

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    db_user = get_user_by_hash_id(db, hash_id)
    if db_user is None:
        return None

    update_data = user.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_balance(db: Session, user_id: int, amount: float, operation: str = "add") -> Optional[models.User]:
    """Обновить баланс пользователя (пополнение или списание).

    Аргументы:
        db:        Сессия базы данных.
        user_id:   Числовой ID пользователя.
        amount:    Сумма операции.
        operation: ``"add"`` — пополнение, ``"subtract"`` — списание.

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    if operation == "add":
        db_user.balance += amount
    elif operation == "subtract":
        db_user.balance -= amount

    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_last_login(db: Session, user_id: int) -> Optional[models.User]:
    """Обновить дату последнего входа пользователя.

    Аргументы:
        db:      Сессия базы данных.
        user_id: Числовой ID пользователя.

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    from datetime import datetime
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    db_user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


def link_merchant_client(db: Session, user_id: int, merchant_client_id: int) -> Optional[models.User]:
    """Привязать ID клиента Merchant API к пользователю.

    Аргументы:
        db:                 Сессия базы данных.
        user_id:            Числовой ID пользователя.
        merchant_client_id: ID клиента в Merchant API.

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    db_user.merchant_client_id = merchant_client_id
    db.commit()
    db.refresh(db_user)
    return db_user


def link_telegram(db: Session, user_id: int, telegram_uid: str) -> Optional[models.User]:
    """Привязать Telegram UID к пользователю.

    Аргументы:
        db:           Сессия базы данных.
        user_id:      Числовой ID пользователя.
        telegram_uid: UID пользователя в Telegram.

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    db_user.telegram_uid = telegram_uid
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_merchant_profile(
    db: Session,
    user_id: int,
    merchant_client_id: Optional[int] = None,
    telegram_uid: Optional[str] = None,
    balance: Optional[float] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    avatar: Optional[str] = None,
    session_token: Optional[str] = None,
) -> Optional[models.User]:
    """Обновить профиль пользователя из данных Merchant API.

    Аргументы:
        db:                 Сессия базы данных.
        user_id:            Числовой ID пользователя.
        merchant_client_id: ID клиента в Merchant API.
        telegram_uid:       UID пользователя в Telegram.
        balance:            Баланс.
        first_name:         Имя.
        last_name:          Фамилия.
        avatar:             URL аватара.
        session_token:      Сессионный токен Merchant API.

    Возвращает:
        Обновлённый объект ``User`` или ``None`` если не найден.
    """
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    if merchant_client_id is not None:
        db_user.merchant_client_id = merchant_client_id
    if telegram_uid is not None:
        db_user.telegram_uid = telegram_uid
    if balance is not None:
        db_user.balance = balance
    if first_name is not None:
        db_user.first_name = first_name
    if last_name is not None:
        db_user.last_name = last_name
    if avatar is not None:
        db_user.avatar = avatar
    if session_token is not None:
        db_user.session_token = session_token

    db.commit()
    db.refresh(db_user)
    return db_user


# =========================================================================
# Пользователи — удаление
# =========================================================================

def delete_user(db: Session, user_id: int) -> bool:
    """Удалить пользователя по числовому ID.

    Аргументы:
        db:      Сессия базы данных.
        user_id: Числовой ID пользователя.

    Возвращает:
        ``True`` если удалён, ``False`` если не найден.
    """
    db_user = get_user(db, user_id)
    if db_user is None:
        return False

    db.delete(db_user)
    db.commit()
    return True


def delete_user_by_hash(db: Session, hash_id: str) -> bool:
    """Удалить пользователя по публичному HASH-идентификатору.

    Аргументы:
        db:      Сессия базы данных.
        hash_id: Публичный HASH-идентификатор.

    Возвращает:
        ``True`` если удалён, ``False`` если не найден.
    """
    db_user = get_user_by_hash_id(db, hash_id)
    if db_user is None:
        return False

    db.delete(db_user)
    db.commit()
    return True
