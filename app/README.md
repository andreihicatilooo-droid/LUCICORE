# app/ — Ядро LUCICORE API

FastAPI-приложение, которое предоставляет REST API для управления пользователями и интеграции с внешним Merchant API.

## Файлы модуля

| Файл | Назначение |
|---|---|
| `main.py` | Точка входа FastAPI: все эндпоинты, lifespan (инициализация БД) |
| `models.py` | SQLAlchemy-модель: `User` |
| `schemas.py` | Pydantic-схемы для валидации запросов и формирования ответов |
| `crud.py` | Функции прямого доступа к БД (create / read / update / delete) |
| `database.py` | Конфигурация движка SQLAlchemy, `SessionLocal`, `init_db()` |
| `security.py` | Хеширование паролей (PBKDF2) + аутентификация ботов (Bearer-токены) |
| `merchant_bridge.py` | Обёртка над Merchant API SDK (`msdk/`) |

## Модели данных (`models.py`)

### User

| Поле | Тип | Описание |
|---|---|---|
| `id` | Integer PK | Автоинкрементный ID |
| `username` | String(255) | Уникальный логин |
| `email` | String(255) | Email (опционально, уникальный) |
| `password_hash` | String(255) | PBKDF2-хеш пароля |
| `first_name`, `last_name` | String(255) | Имя, фамилия |
| `avatar` | String(500) | URL аватара |
| `is_active` | Boolean | Активен ли аккаунт |
| `is_verified` | Boolean | Подтверждён ли |
| `balance` | Float | Баланс пользователя |
| `merchant_client_id` | Integer | ID клиента в Merchant API |
| `telegram_uid` | String(255) | Telegram UID |
| `session_token` | String(500) | Сессионный токен Merchant API |
| `created_at`, `updated_at`, `last_login` | DateTime | Временные метки |

## CRUD-функции (`crud.py`)

### Users

| Функция | Описание |
|---|---|
| `get_user(db, user_id)` | Получить пользователя по ID |
| `get_user_by_username(db, username)` | Найти по логину |
| `get_user_by_email(db, email)` | Найти по email |
| `get_user_by_merchant_client_id(db, id)` | Найти по merchant client ID |
| `get_user_by_telegram_uid(db, uid)` | Найти по Telegram UID |
| `get_users(db, skip, limit)` | Список пользователей с пагинацией |
| `create_user(db, user, password_hash)` | Создать пользователя |
| `update_user(db, user_id, user)` | Обновить профиль |
| `update_user_balance(db, user_id, amount, op)` | Изменить баланс (add / subtract) |
| `update_user_last_login(db, user_id)` | Обновить `last_login` |
| `link_merchant_client(db, user_id, id)` | Привязать merchant client ID |
| `link_telegram(db, user_id, uid)` | Привязать Telegram UID |
| `update_user_merchant_profile(db, …)` | Синхронизировать все поля из Merchant API |
| `delete_user(db, user_id)` | Удалить пользователя |

## Безопасность (`security.py`)

### Хеширование паролей

| Функция | Описание |
|---|---|
| `hash_password(password)` | PBKDF2-SHA256, 100 000 итераций, случайная 16-байтовая соль |
| `verify_password(password, stored_hash)` | Безопасная проверка (hmac.compare_digest) |

### Аутентификация ботов (Bearer-токены)

| Функция / Depends | Описание |
|---|---|
| `generate_api_token()` | Генерация случайного URL-safe токена (43 символа) |
| `require_bot_token` | FastAPI Depends — проверяет `Authorization: Bearer <token>`. Возвращает имя бота (`bot_sales`, `bot_admin`, …). 401 если нет заголовка, 403 при неверном токене |
| `optional_bot_token` | То же, но без ошибки при отсутствии заголовка (для публичных эндпоинтов) |

Токены загружаются из переменных окружения:
- `BOT_SALES_API_TOKEN` → `bot_sales`
- `BOT_ADMIN_API_TOKEN` → `bot_admin`
- `BOT_SUPPORT_API_TOKEN` → `bot_support`
- `BOT_NOTIFY_API_TOKEN` → `bot_notify`

Если ни одна переменная не задана — dev-режим: авторизация пропускается.

## Merchant Bridge (`merchant_bridge.py`)

Обёртка над SDK из `msdk/`, предоставляет:

| Метод | Описание |
|---|---|
| `MerchantBridge.from_env()` | Создать экземпляр из переменных окружения |
| `get_captcha()` | Получить капчу для регистрации/логина |
| `register_web_client(captcha_id, answer)` | Зарегистрировать нового клиента + получить профиль |
| `get_profile(session_token)` | Получить профиль по сессионному токену |
| `login_web_client(auth_code, captcha_id, answer)` | Логин через Web Client API |
| `search_clients(query, limit)` | Поиск клиентов через Merchant API |

## Конфигурация БД (`database.py`)

- По умолчанию: `sqlite:///./lucicore.db`
- Настраивается через `DATABASE_URL` в `.env`
- `init_db()` — создаёт все таблицы при старте приложения
- `get_db()` — FastAPI Depends для получения сессии

## Эндпоинты (`main.py`)

Подробная таблица — в корневом [README.md](../README.md#api-endpoints).

Ключевые правила:
- **GET** — публичный доступ (без токена)
- **POST / PUT / DELETE** — требуют `Authorization: Bearer <token>` (Depends `require_bot_token`)
- Merchant-эндпоинты возвращают 503, если SDK не настроен
