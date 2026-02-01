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


# User schemas (based on Merchant API structure)
class UserBase(BaseModel):
    """Base schema for User."""
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a User."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating a User."""
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserBalanceUpdate(BaseModel):
    """Schema for updating user balance."""
    amount: float
    operation: str = "add"  # "add" or "subtract"


class User(UserBase):
    """Schema for User response."""
    id: int
    is_active: bool
    is_verified: bool
    balance: float
    merchant_client_id: Optional[int] = None
    telegram_uid: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
