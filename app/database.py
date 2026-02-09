"""
Конфигурация базы данных и управление сессиями.

По умолчанию используется SQLite (``sqlite:///./lucicore.db``).
Для смены СУБД достаточно установить переменную окружения ``DATABASE_URL``.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
import os

# URL подключения к БД — по умолчанию SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lucicore.db")


# ---------------------------------------------------------------------------
# SQLite-совместимость: JSONB → JSON
# ---------------------------------------------------------------------------
# PostgreSQL-тип JSONB не поддерживается SQLite.  Регистрируем fallback,
# чтобы при использовании SQLite колонки JSONB создавались как JSON (TEXT).
@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(type_, compiler, **kw):
    return "JSON"

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
