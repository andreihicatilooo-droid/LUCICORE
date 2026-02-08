"""
Конфигурация базы данных и управление сессиями.

По умолчанию используется SQLite (``sqlite:///./lucicore.db``).
Для смены СУБД достаточно установить переменную окружения ``DATABASE_URL``.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# URL подключения к БД — по умолчанию SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lucicore.db")

# Движок SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Фабрика локальных сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей
Base = declarative_base()


def get_db():
    """FastAPI-зависимость: предоставляет сессию БД.

    Сессия автоматически закрывается после завершения запроса.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создать все таблицы в БД (если не существуют).

    Вызывается при старте сервера в ``lifespan`` (см. ``main.py``).
    """
    Base.metadata.create_all(bind=engine)
