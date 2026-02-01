"""CRUD operations for database."""
from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas


# Item CRUD operations
def get_item(db: Session, item_id: int) -> Optional[models.Item]:
    """Get a single item by ID."""
    return db.query(models.Item).filter(models.Item.id == item_id).first()


def get_items(db: Session, skip: int = 0, limit: int = 100) -> List[models.Item]:
    """Get a list of items."""
    return db.query(models.Item).offset(skip).limit(limit).all()


def create_item(db: Session, item: schemas.ItemCreate) -> models.Item:
    """Create a new item."""
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_item(db: Session, item_id: int, item: schemas.ItemUpdate) -> Optional[models.Item]:
    """Update an existing item."""
    db_item = get_item(db, item_id)
    if db_item is None:
        return None
    
    update_data = item.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: int) -> bool:
    """Delete an item."""
    db_item = get_item(db, item_id)
    if db_item is None:
        return False
    
    db.delete(db_item)
    db.commit()
    return True


# Service CRUD operations
def get_service(db: Session, service_id: int) -> Optional[models.Service]:
    """Get a single service by ID."""
    return db.query(models.Service).filter(models.Service.id == service_id).first()


def get_service_by_name(db: Session, name: str) -> Optional[models.Service]:
    """Get a service by name."""
    return db.query(models.Service).filter(models.Service.name == name).first()


def get_services(db: Session, skip: int = 0, limit: int = 100) -> List[models.Service]:
    """Get a list of services."""
    return db.query(models.Service).offset(skip).limit(limit).all()


def create_service(db: Session, service: schemas.ServiceCreate) -> models.Service:
    """Create a new service."""
    db_service = models.Service(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


def update_service(db: Session, service_id: int, service: schemas.ServiceUpdate) -> Optional[models.Service]:
    """Update an existing service."""
    db_service = get_service(db, service_id)
    if db_service is None:
        return None
    
    update_data = service.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_service, key, value)
    
    db.commit()
    db.refresh(db_service)
    return db_service


def delete_service(db: Session, service_id: int) -> bool:
    """Delete a service."""
    db_service = get_service(db, service_id)
    if db_service is None:
        return False

    db.delete(db_service)
    db.commit()
    return True


# User CRUD operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Get a single user by ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get a user by username."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get a user by email."""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_merchant_client_id(db: Session, merchant_client_id: int) -> Optional[models.User]:
    """Get a user by merchant API client ID."""
    return db.query(models.User).filter(models.User.merchant_client_id == merchant_client_id).first()


def get_user_by_telegram_uid(db: Session, telegram_uid: str) -> Optional[models.User]:
    """Get a user by Telegram UID."""
    return db.query(models.User).filter(models.User.telegram_uid == telegram_uid).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Get a list of users."""
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate, password_hash: str) -> models.User:
    """Create a new user."""
    user_data = user.model_dump(exclude={"password"})
    db_user = models.User(**user_data, password_hash=password_hash)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: schemas.UserUpdate) -> Optional[models.User]:
    """Update an existing user."""
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    update_data = user.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_balance(db: Session, user_id: int, amount: float, operation: str = "add") -> Optional[models.User]:
    """Update user balance (add or subtract)."""
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
    """Update user's last login timestamp."""
    from datetime import datetime
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    db_user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


def link_merchant_client(db: Session, user_id: int, merchant_client_id: int) -> Optional[models.User]:
    """Link a merchant API client ID to user."""
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    db_user.merchant_client_id = merchant_client_id
    db.commit()
    db.refresh(db_user)
    return db_user


def link_telegram(db: Session, user_id: int, telegram_uid: str) -> Optional[models.User]:
    """Link a Telegram UID to user."""
    db_user = get_user(db, user_id)
    if db_user is None:
        return None

    db_user.telegram_uid = telegram_uid
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user."""
    db_user = get_user(db, user_id)
    if db_user is None:
        return False

    db.delete(db_user)
    db.commit()
    return True
