# shared/ — Общие модули для ботов

Содержит переиспользуемый код, который подключают все Telegram-боты (`bots/bot_*`).

## lucicore_client.py

Асинхронный HTTP-клиент для взаимодействия с LUCICORE API. Построен на `httpx.AsyncClient`.

### Быстрый старт

```python
from shared.lucicore_client import LucicoreClient

async with LucicoreClient(
    base_url="http://127.0.0.1:8000",
    api_token="change-me-sales-token",
) as client:
    health = await client.health()       # {"status": "healthy"}
    users = await client.get_users()     # [{"id": 1, "username": "..."}]
    user = await client.create_user(username="alice", password="secret")
```

### Параметры конструктора

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `base_url` | `str` | `http://127.0.0.1:8000` | Адрес LUCICORE API |
| `api_token` | `str \| None` | `None` | Bearer-токен для авторизации |
| `timeout` | `float` | `30.0` | Таймаут на запрос (секунды) |
| `max_retries` | `int` | `3` | Максимум повторных попыток |

### Lifecycle

Клиент реализует `async with` (контекстный менеджер):

```python
# Вариант 1: через async with (рекомендуется)
async with LucicoreClient(...) as client:
    ...

# Вариант 2: ручное управление
client = LucicoreClient(...)
try:
    ...
finally:
    await client.close()
```

### Обработка ошибок

- **Retry** — автоматически повторяет запрос при HTTP 502/503/504 и транспортных ошибках
- **Backoff** — задержка между повторами: `0.5 × attempt` секунд
- **Таймаут** — 30 секунд на запрос (настраивается)
- **Логирование** — предупреждения при retry, ошибки при неудачных запросах

При ошибке выбрасывается `LucicoreAPIError`:

```python
from shared.lucicore_client import LucicoreClient, LucicoreAPIError

try:
    user = await client.get_user(999)
except LucicoreAPIError as e:
    print(e.status_code)  # 404
    print(e.detail)       # "User not found"
```

### Реализованные методы

#### Health

| Метод | Возвращает | Описание |
|---|---|---|
| `health()` | `dict` | Проверка доступности ядра (`GET /health`) |

#### Users

| Метод | Возвращает | Описание |
|---|---|---|
| `get_users(skip, limit)` | `list[dict]` | Список пользователей |
| `get_user(user_id)` | `dict` | Пользователь по ID |
| `create_user(username, password, **kwargs)` | `dict` | Создать пользователя |
| `update_user(user_id, **fields)` | `dict` | Обновить поля пользователя |
| `delete_user(user_id)` | `dict` | Удалить пользователя |

#### Merchant Bridge

| Метод | Возвращает | Описание |
|---|---|---|
| `get_captcha()` | `dict` | Получить капчу (`captcha_id`, `image`) |
| `register_merchant(user_id, captcha_id, captcha_answer)` | `dict` | Зарегистрировать пользователя в Merchant API |
| `sync_merchant(user_id)` | `dict` | Синхронизировать профиль из Merchant API |

### Пример использования в боте

```python
import os
from aiogram import Bot, Dispatcher, types
from shared.lucicore_client import LucicoreClient

bot = Bot(token=os.getenv("BOT_SALES_TELEGRAM_TOKEN"))
dp = Dispatcher()

# Создать клиент один раз при старте бота
luci = LucicoreClient(
    base_url=os.getenv("LUCICORE_API_URL", "http://127.0.0.1:8000"),
    api_token=os.getenv("BOT_SALES_API_TOKEN"),
)

@dp.message(commands=["users"])
async def list_users(message: types.Message):
    users = await luci.get_users()
    if not users:
        await message.answer("Пользователей пока нет.")
        return
    text = "\n".join(f"• {u['username']} (id={u['id']})" for u in users)
    await message.answer(text)
```
