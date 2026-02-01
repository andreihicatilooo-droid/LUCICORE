"""Pydantic schemas for API validation."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ItemBase(BaseModel):
    """Base schema for Item."""
    name: str
    description: Optional[str] = None


class ItemCreate(ItemBase):
    """Schema for creating an Item."""
    pass


class ItemUpdate(BaseModel):
    """Schema for updating an Item."""
    name: Optional[str] = None
    description: Optional[str] = None


class Item(ItemBase):
    """Schema for Item response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceBase(BaseModel):
    """Base schema for Service."""
    name: str
    description: Optional[str] = None
    endpoint: Optional[str] = None


class ServiceCreate(ServiceBase):
    """Schema for creating a Service."""
    pass


class ServiceUpdate(BaseModel):
    """Schema for updating a Service."""
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint: Optional[str] = None


class Service(ServiceBase):
    """Schema for Service response."""
    id: int
    created_at: datetime
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
