"""
Основное приложение LUCICORE API.

FastAPI-приложение с REST-эндпоинтами для управления пользователями
и интеграции с Merchant / Web Client API.

Все публичные эндпоинты используют ``hash_id`` вместо числового ``id``
для идентификации пользователей.
"""
import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app import crud, schemas
from app.database import get_db, init_db
from app.merchant_bridge import MerchantBridge
from app.security import hash_password, require_bot_token

logger = logging.getLogger(__name__)

load_dotenv()


# ---------------------------------------------------------------------------
# Жизненный цикл приложения
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация таблиц БД при старте сервера."""
    init_db()
    yield


# Создание экземпляра FastAPI
app = FastAPI(
    title="LUCICORE API",
    description="Единый API-сервер для экосистемы ботов LUCICORE",
    version="1.0.0",
    lifespan=lifespan,
)


def get_merchant_bridge() -> MerchantBridge:
    """Создать экземпляр MerchantBridge из переменных окружения."""
    try:
        return MerchantBridge.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# =========================================================================
# Корневой эндпоинт
# =========================================================================

@app.get("/")
def read_root():
    """Корневой эндпоинт с общей информацией об API."""
    return {
        "message": "Добро пожаловать в LUCICORE API",
        "version": "1.0.0",
        "endpoints": {
            "users": "/users",
            "user_by_hash": "/users/hash/{hash_id}",
            "merchant_captcha": "/merchant/captcha",
            "health": "/health",
        },
    }


# =========================================================================
# Проверка здоровья
# =========================================================================

@app.get("/health")
def health_check():
    """Эндпоинт проверки доступности сервера."""
    return {"status": "healthy"}


# =========================================================================
# Эндпоинты пользователей
# =========================================================================

@app.post("/users/", response_model=schemas.User, status_code=201)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    _caller: str = Depends(require_bot_token),
):
    """Создать нового пользователя.

    ``hash_id`` генерируется автоматически и возвращается в ответе.
    Требует Bearer-токен бота.
    """
    if crud.get_user_by_username(db, username=user.username):
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    if user.email and crud.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="E-mail уже используется")
    password_hash = hash_password(user.password)
    return crud.create_user(db=db, user=user, password_hash=password_hash)


@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получить список пользователей с пагинацией."""
    return crud.get_users(db, skip=skip, limit=limit)


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Получить пользователя по числовому ID (внутренний, для совместимости)."""
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


@app.get("/users/hash/{hash_id}", response_model=schemas.User)
def read_user_by_hash(hash_id: str, db: Session = Depends(get_db)):
    """Получить пользователя по публичному HASH-идентификатору.

    Это основной способ идентификации пользователя в публичных запросах.
    """
    db_user = crud.get_user_by_hash_id(db, hash_id=hash_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _caller: str = Depends(require_bot_token),
):
    """Обновить пользователя по числовому ID. Требует Bearer-токен."""
    if user.username:
        existing = crud.get_user_by_username(db, username=user.username)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    if user.email:
        existing = crud.get_user_by_email(db, email=user.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="E-mail уже используется")
    db_user = crud.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


@app.put("/users/hash/{hash_id}", response_model=schemas.User)
def update_user_by_hash(
    hash_id: str,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _caller: str = Depends(require_bot_token),
):
    """Обновить пользователя по HASH-идентификатору. Требует Bearer-токен."""
    if user.username:
        existing = crud.get_user_by_username(db, username=user.username)
        if existing and existing.hash_id != hash_id:
            raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    if user.email:
        existing = crud.get_user_by_email(db, email=user.email)
        if existing and existing.hash_id != hash_id:
            raise HTTPException(status_code=400, detail="E-mail уже используется")
    db_user = crud.update_user_by_hash(db, hash_id=hash_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _caller: str = Depends(require_bot_token),
):
    """Удалить пользователя по числовому ID. Требует Bearer-токен."""
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"message": "Пользователь успешно удалён"}


@app.delete("/users/hash/{hash_id}")
def delete_user_by_hash(
    hash_id: str,
    db: Session = Depends(get_db),
    _caller: str = Depends(require_bot_token),
):
    """Удалить пользователя по HASH-идентификатору. Требует Bearer-токен."""
    success = crud.delete_user_by_hash(db, hash_id=hash_id)
    if not success:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"message": "Пользователь успешно удалён"}


# =========================================================================
# Эндпоинты Merchant API / Web Client API
# =========================================================================

@app.get("/merchant/captcha", response_model=schemas.MerchantCaptcha)
def get_merchant_captcha(bridge: MerchantBridge = Depends(get_merchant_bridge)):
    """Получить капчу для регистрации/входа в Web Client API."""
    try:
        data = bridge.get_captcha()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return schemas.MerchantCaptcha(captcha_id=data["captcha_id"], image=data["image"])


@app.post("/users/{user_id}/merchant/register", response_model=schemas.MerchantLinkResponse)
def register_user_with_merchant(
    user_id: int,
    payload: schemas.MerchantLinkRequest,
    db: Session = Depends(get_db),
    bridge: MerchantBridge = Depends(get_merchant_bridge),
    _caller: str = Depends(require_bot_token),
):
    """Зарегистрировать пользователя в Web Client API и связать 1:1.

    Требует Bearer-токен бота.  Возвращает ``hash_id``, ``merchant_client_id``
    и ``auth_code`` для дальнейших операций.
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    try:
        result = bridge.register_web_client(payload.captcha_id, payload.captcha_answer)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    profile = result.get("profile") or {}
    db_user = crud.update_user_merchant_profile(
        db=db,
        user_id=user_id,
        merchant_client_id=profile.get("pk"),
        telegram_uid=profile.get("uid"),
        balance=profile.get("balance"),
        first_name=profile.get("first_name"),
        last_name=profile.get("last_name"),
        avatar=profile.get("avatar"),
        session_token=result.get("token"),
    )
    if db_user is None or db_user.merchant_client_id is None:
        raise HTTPException(status_code=502, detail="Не удалось привязать профиль Merchant API")

    auth_code = result.get("auth_code")
    if not auth_code:
        raise HTTPException(status_code=502, detail="Merchant API не вернул auth_code")

    return schemas.MerchantLinkResponse(
        hash_id=db_user.hash_id,
        merchant_client_id=db_user.merchant_client_id,
        auth_code=auth_code,
    )


@app.post("/users/{user_id}/merchant/sync", response_model=schemas.User)
def sync_user_from_merchant(
    user_id: int,
    db: Session = Depends(get_db),
    bridge: MerchantBridge = Depends(get_merchant_bridge),
    _caller: str = Depends(require_bot_token),
):
    """Синхронизировать профиль пользователя из Web Client API в локальную БД.

    Требует Bearer-токен бота.
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not db_user.session_token:
        raise HTTPException(status_code=400, detail="Пользователь не привязан к Web Client API")

    try:
        profile = bridge.get_profile(db_user.session_token)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    db_user = crud.update_user_merchant_profile(
        db=db,
        user_id=user_id,
        merchant_client_id=profile.get("pk"),
        telegram_uid=profile.get("uid"),
        balance=profile.get("balance"),
        first_name=profile.get("first_name"),
        last_name=profile.get("last_name"),
        avatar=profile.get("avatar"),
    )
    if db_user is None:
        raise HTTPException(status_code=502, detail="Не удалось синхронизировать профиль")
    return db_user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
