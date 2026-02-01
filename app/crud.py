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
