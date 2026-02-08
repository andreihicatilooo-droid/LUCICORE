# LUCICORE

Центральное ядро (REST API + база данных) для экосистемы Telegram-ботов. Все боты обращаются к единому API, данные хранятся в одном месте.

## Архитектура

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  bot_sales   │  │  bot_admin   │  │ bot_support  │  │  bot_notify  │
│  (aiogram)   │  │  (aiogram)   │  │  (aiogram)   │  │  (aiogram)   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       │     Authorization: Bearer <token>                  │
       └──────────────┐  │  ┌──────────────┘  ┌─────────────┘
                      ▼  ▼  ▼                 ▼
              ┌─────────────────────────┐
              │     LUCICORE API        │
              │  FastAPI · SQLAlchemy   │
              │  port 8000              │
              └────────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              │    Database (SQLite /   │
              │    PostgreSQL / MySQL)  │
              └─────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │   Merchant API (msdk)   │
              │   Web Client bridge     │
              └─────────────────────────┘
```

## Возможности

- **REST API** — полный CRUD для Users + интеграция с Merchant API
- **Аутентификация ботов** — Bearer-токены из `.env`, валидация через `require_bot_token`
- **Merchant API Bridge** — капча, регистрация, синхронизация профилей через внешний торговый API
- **Единый HTTP-клиент** (`shared/lucicore_client.py`) — асинхронный клиент на `httpx` для всех ботов
- **Swagger / ReDoc** — автодокументация по `/docs` и `/redoc`
- **Health check** — `GET /health`

## Структура проекта

```
LUCICORE/
├── app/                          # Ядро API (FastAPI)
│   ├── main.py                   # Эндпоинты, lifespan, приложение
│   ├── models.py                 # SQLAlchemy-модели: User
│   ├── schemas.py                # Pydantic-схемы запросов/ответов
│   ├── crud.py                   # CRUD-операции над БД
│   ├── database.py               # Engine, SessionLocal, init_db()
│   ├── security.py               # Хеширование паролей + Bearer-аутентификация
│   └── merchant_bridge.py        # Обёртка над Merchant API SDK
├── shared/                       # Общие модули для ботов
│   └── lucicore_client.py        # Async HTTP-клиент к LUCICORE API
├── bots/                         # Telegram-боты (aiogram 3)
│   ├── bot_sales/                # Бот продаж
│   ├── bot_admin/                # Бот администрирования
│   ├── bot_support/              # Бот поддержки
│   └── bot_notify/               # Бот уведомлений
├── msdk/                         # Merchant API SDK (локальный пакет)
├── run.py                        # Точка запуска API-сервера
├── requirements.txt              # Python-зависимости
├── .env.example                  # Шаблон переменных окружения
└── README.md
```

## Быстрый старт

### 1. Клонировать и установить

```bash
git clone https://github.com/andreihicatilooo-droid/LUCICORE.git
cd LUCICORE
pip install -r requirements.txt
```

### 2. Настроить окружение

```bash
cp .env.example .env
# Отредактировать .env: DATABASE_URL, MERCHANT_*, токены ботов
```

### 3. Запустить API

```bash
# Через run.py (рекомендуется)
RELOAD=true python run.py

# Или напрямую через uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API доступен по адресу: `http://localhost:8000`

## Переменные окружения (.env)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `DATABASE_URL` | URL базы данных | `sqlite:///./lucicore.db` |
| `MERCHANT_API_BASE_URL` | Базовый URL Merchant API | — |
| `MERCHANT_API_KEY` | API-ключ мерчанта | — |
| `MERCHANT_API_SECRET` | Секрет мерчанта | — |
| `MERCHANT_USE_TOR` | Использовать Tor-прокси | `false` |
| `MERCHANT_TOR_PROXY` | Адрес Tor SOCKS5-прокси | `socks5h://127.0.0.1:9050` |
| `BOT_SALES_TELEGRAM_TOKEN` | Telegram-токен бота продаж | — |
| `BOT_ADMIN_TELEGRAM_TOKEN` | Telegram-токен бота администрирования | — |
| `BOT_SUPPORT_TELEGRAM_TOKEN` | Telegram-токен бота поддержки | — |
| `BOT_NOTIFY_TELEGRAM_TOKEN` | Telegram-токен бота уведомлений | — |
| `BOT_SALES_API_TOKEN` | Bearer-токен bot_sales для LUCICORE | — |
| `BOT_ADMIN_API_TOKEN` | Bearer-токен bot_admin для LUCICORE | — |
| `BOT_SUPPORT_API_TOKEN` | Bearer-токен bot_support для LUCICORE | — |
| `BOT_NOTIFY_API_TOKEN` | Bearer-токен bot_notify для LUCICORE | — |
| `LUCICORE_API_URL` | URL ядра (для ботов) | `http://127.0.0.1:8000` |

## API Endpoints

### Общие (без авторизации)

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Информация об API |
| `GET` | `/health` | Health-check |

### Users — требуют Bearer-токен для мутаций

| Метод | Путь | Авторизация | Описание |
|---|---|---|---|
| `GET` | `/users/` | — | Список пользователей |
| `GET` | `/users/{id}` | — | Пользователь по ID |
| `POST` | `/users/` | Bearer | Создать пользователя |
| `PUT` | `/users/{id}` | Bearer | Обновить пользователя |
| `DELETE` | `/users/{id}` | Bearer | Удалить пользователя |

### Merchant Bridge — требуют Bearer-токен

| Метод | Путь | Авторизация | Описание |
|---|---|---|---|
| `GET` | `/merchant/captcha` | — | Получить капчу |
| `POST` | `/users/{id}/merchant/register` | Bearer | Зарегистрировать в Merchant API |
| `POST` | `/users/{id}/merchant/sync` | Bearer | Синхронизировать профиль из Merchant API |

## Аутентификация

Все **POST / PUT / DELETE** эндпоинты защищены Bearer-токенами. В заголовке запроса:

```
Authorization: Bearer <BOT_*_API_TOKEN>
```

- Токены задаются в `.env` (`BOT_SALES_API_TOKEN`, `BOT_ADMIN_API_TOKEN` и т.д.)
- Если ни один токен не задан — режим разработки (авторизация пропускается)
- `GET`-эндпоинты остаются публичными

## Боты

Все боты строятся на **aiogram 3** и используют `shared/lucicore_client.py` для связи с ядром.

| Бот | Папка | Назначение | Реализованные функции |
|---|---|---|---|
| **bot_sales** | `bots/bot_sales/` | Продажи через Telegram | Просмотр баланса, регистрация через Merchant API, управление профилем |
| **bot_admin** | `bots/bot_admin/` | Администрирование | CRUD пользователей, просмотр статистики, управление балансами |
| **bot_support** | `bots/bot_support/` | Поддержка пользователей | Просмотр профиля пользователя, проверка статуса, синхронизация с Merchant API |
| **bot_notify** | `bots/bot_notify/` | Уведомления | Рассылка сообщений, оповещения об изменении статуса, массовые уведомления |

Каждый бот получает свой `BOT_*_TELEGRAM_TOKEN` (для Telegram) и `BOT_*_API_TOKEN` (для доступа к LUCICORE API).

## Примеры использования

### cURL — создание пользователя (с авторизацией)

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me-sales-token" \
  -d '{"username": "john", "password": "secret123"}'
```

### Python — использование общего клиента (из бота)

```python
from shared.lucicore_client import LucicoreClient

async def main():
    async with LucicoreClient(
        base_url="http://127.0.0.1:8000",
        api_token="change-me-sales-token",
    ) as client:
        # Проверить доступность ядра
        health = await client.health()

        # Создать пользователя
        user = await client.create_user(username="john", password="secret123")

        # Получить список пользователей
        users = await client.get_users()

        # Зарегистрировать в Merchant API
        result = await client.register_merchant(
            user["id"], captcha_id="abc", captcha_answer="xyz"
        )
```

## Документация API

После запуска:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Требования

- Python 3.10+
- FastAPI, SQLAlchemy, Pydantic
- httpx (для `LucicoreClient`)
- aiogram 3 (для ботов)
- Uvicorn

## Лицензия

MIT