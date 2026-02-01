"""Database models."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.sql import func
from app.database import Base


class Item(Base):
    """Item model for storing generic items."""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Service(Base):
    """Service model for tracking connected services."""
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    endpoint = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    """User model based on Merchant API structure."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile fields
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    avatar = Column(String(500), nullable=True)

    # Status flags
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Balance (from merchant_api client balance feature)
    balance = Column(Float, default=0.0)

    # Merchant API integration fields
    merchant_client_id = Column(Integer, nullable=True, index=True)
    telegram_uid = Column(String(255), nullable=True, unique=True)
    session_token = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
