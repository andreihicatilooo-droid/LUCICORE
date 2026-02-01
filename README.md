# LUCICORE

База данных с REST API для подключения нескольких сервисов.

## Описание

LUCICORE - это REST API сервис с базой данных, который позволяет нескольким сервисам подключаться и работать с общими данными. API построен на FastAPI и использует SQLAlchemy для работы с базой данных.

## Возможности

- REST API с документацией OpenAPI (Swagger)
- Управление элементами (Items) - CRUD операции
- Управление сервисами (Services) - регистрация и отслеживание подключенных сервисов
- SQLite база данных по умолчанию (легко настраивается на PostgreSQL/MySQL)
- Автоматическая инициализация базы данных
- Health check endpoint

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/andreihicatilooo-droid/LUCICORE.git
cd LUCICORE
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

### Вариант 1: Через uvicorn
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Вариант 2: Через Python
```bash
python -m app.main
```

API будет доступен по адресу: `http://localhost:8000`

## Документация API

После запуска сервера, документация API доступна по следующим адресам:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Основные

- `GET /` - Информация об API
- `GET /health` - Проверка состояния сервиса

### Items (Элементы)

- `POST /items/` - Создать новый элемент
- `GET /items/` - Получить список элементов
- `GET /items/{item_id}` - Получить элемент по ID
- `PUT /items/{item_id}` - Обновить элемент
- `DELETE /items/{item_id}` - Удалить элемент

### Services (Сервисы)

- `POST /services/` - Зарегистрировать новый сервис
- `GET /services/` - Получить список сервисов
- `GET /services/{service_id}` - Получить сервис по ID
- `PUT /services/{service_id}` - Обновить информацию о сервисе
- `DELETE /services/{service_id}` - Удалить сервис

## Примеры использования

### Создание элемента
```bash
curl -X POST "http://localhost:8000/items/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "description": "This is a test item"}'
```

### Получение всех элементов
```bash
curl -X GET "http://localhost:8000/items/"
```

### Регистрация сервиса
```bash
curl -X POST "http://localhost:8000/services/" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Service", "description": "Service description", "endpoint": "http://service.example.com"}'
```

### Получение всех сервисов
```bash
curl -X GET "http://localhost:8000/services/"
```

## Конфигурация

### База данных

По умолчанию используется SQLite (`lucicore.db`). Для использования другой базы данных, установите переменную окружения `DATABASE_URL`:

```bash
# PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost/dbname"

# MySQL
export DATABASE_URL="mysql://user:password@localhost/dbname"
```

## Структура проекта

```
LUCICORE/
├── app/
│   ├── __init__.py
│   ├── main.py          # Главный файл приложения FastAPI
│   ├── database.py      # Конфигурация базы данных
│   ├── models.py        # SQLAlchemy модели
│   ├── schemas.py       # Pydantic схемы для валидации
│   └── crud.py          # CRUD операции
├── requirements.txt     # Python зависимости
└── README.md           # Документация
```

## Подключение из других сервисов

### Python
```python
import requests

# Создание элемента
response = requests.post(
    "http://localhost:8000/items/",
    json={"name": "New Item", "description": "Description"}
)
item = response.json()

# Получение элементов
response = requests.get("http://localhost:8000/items/")
items = response.json()
```

### JavaScript/Node.js
```javascript
// Создание элемента
const response = await fetch('http://localhost:8000/items/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'New Item',
    description: 'Description'
  })
});
const item = await response.json();

// Получение элементов
const response = await fetch('http://localhost:8000/items/');
const items = await response.json();
```

## Требования

- Python 3.8+
- FastAPI
- SQLAlchemy
- Uvicorn

## Лицензия

MIT