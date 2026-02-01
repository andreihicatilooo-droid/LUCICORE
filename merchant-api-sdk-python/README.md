# Merchant API SDK для Python

## Установка

```bash
pip install -e .           # Базовая установка
pip install -e .[tor]      # С поддержкой TOR (рекомендуется)
```

## Настройка TOR (рекомендуется)

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y tor
sudo systemctl enable tor && sudo systemctl start tor

# CentOS/RHEL
sudo yum install -y epel-release tor
sudo systemctl enable tor && sudo systemctl start tor

# macOS
brew install tor && brew services start tor

# Проверка работы TOR
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip
# Должно вернуть: {"IsTor":true, ...}
```

## Быстрый старт

```python
from merchant_api import MerchantApiClient

client = MerchantApiClient(
    base_url="https://your-api-domain.com",
    api_key="your-api-key",
    api_secret="your-api-secret",
    use_tor=True,  # По умолчанию True (рекомендуется)
    tor_proxy="socks5h://127.0.0.1:9050"  # Опционально
)

# Проверка подключения через TOR
if client.check_tor_connection():
    print("Подключение через TOR активно")
```

---

## Примеры использования

### 1. Главная страница - информация о магазине

Получение основной информации о магазине для отображения на главной странице.

```python
from merchant_api import MerchantApiClient

client = MerchantApiClient(
    base_url="https://your-api-domain.com",
    api_key="your-api-key",
    api_secret="your-api-secret"
)

# Получаем информацию о магазине
merchant = client.get_merchant()
print(merchant)
```

**Ответ сервера:**
```json
{
    "id": 42,
    "title": "Premium Shop",
    "currency": "RUB",
    "avatar": "https://cdn.example.com/avatars/shop42.jpg",
    "description": "Лучший магазин с быстрой доставкой",
    "is_working": true,
    "min_order_amount": 1000.0,
    "cities_count": 15,
    "products_count": 128,
    "reviews_count": 4521,
    "average_rating": 4.8
}
```

**Использование в приложении:**
```python
def render_main_page():
    merchant = client.get_merchant()

    return {
        "shop_name": merchant["title"],
        "logo": merchant["avatar"],
        "description": merchant["description"],
        "rating": f"{merchant['average_rating']:.1f}",
        "reviews_count": merchant["reviews_count"],
        "is_open": merchant["is_working"]
    }
```

---

### 2. Формирование витрины товаров

#### Способ 1: Витрина по городам (географическая навигация)

Подходит когда пользователь сначала выбирает город, затем видит доступные товары.

```python
# Шаг 1: Получаем список городов
cities = client.get_cities()
print(cities)
```

**Ответ сервера:**
```json
[
    {"id": 1, "name": "Москва", "products_count": 45},
    {"id": 2, "name": "Санкт-Петербург", "products_count": 38},
    {"id": 3, "name": "Казань", "products_count": 22},
    {"id": 4, "name": "Новосибирск", "products_count": 18},
    {"id": 5, "name": "Екатеринбург", "products_count": 15}
]
```

```python
# Шаг 2: Пользователь выбрал Москву (id=1), получаем товары
products = client.get_products(city_id=1)
print(products)
```

**Ответ сервера:**
```json
[
    {
        "id": 101,
        "name": "Товар Премиум",
        "description": "Высококачественный товар",
        "price": 5000.0,
        "currency": "RUB",
        "in_stock": true,
        "locations_count": 12,
        "image": "https://cdn.example.com/products/101.jpg"
    },
    {
        "id": 102,
        "name": "Товар Стандарт",
        "description": "Отличное соотношение цена/качество",
        "price": 2500.0,
        "currency": "RUB",
        "in_stock": true,
        "locations_count": 8,
        "image": "https://cdn.example.com/products/102.jpg"
    }
]
```

```python
# Шаг 3: Получаем локации для выбранного города
locations = client.get_locations(city_id=1)
print(locations)
```

**Ответ сервера:**
```json
[
    {
        "id": 201,
        "name": "Центральный район",
        "parent_id": null,
        "sublocations": [
            {"id": 211, "name": "Арбат", "parent_id": 201},
            {"id": 212, "name": "Тверская", "parent_id": 201}
        ]
    },
    {
        "id": 202,
        "name": "Северный район",
        "parent_id": null,
        "sublocations": [
            {"id": 221, "name": "Речной вокзал", "parent_id": 202},
            {"id": 222, "name": "Водный стадион", "parent_id": 202}
        ]
    }
]
```

**Полный пример витрины по городам:**
```python
def build_catalog_by_city():
    """Формирование витрины с навигацией: Город -> Товары -> Локации"""

    # 1. Получаем все города
    cities = client.get_cities()

    catalog = {}
    for city in cities:
        city_id = city["id"]

        # 2. Для каждого города получаем товары и локации
        products = client.get_products(city_id=city_id)
        locations = client.get_locations(city_id=city_id)

        catalog[city["name"]] = {
            "city_id": city_id,
            "products": products,
            "locations": locations,
            "products_count": len(products)
        }

    return catalog

# Использование
catalog = build_catalog_by_city()
print(f"Доступно городов: {len(catalog)}")
print(f"Товаров в Москве: {catalog['Москва']['products_count']}")
```

#### Способ 2: Витрина по видам товаров (категорийная навигация)

Подходит когда пользователь сначала выбирает тип товара, затем город/локацию.

```python
def build_catalog_by_product_type():
    """Формирование витрины: Тип товара -> Города где доступен -> Локации"""

    # 1. Получаем все города
    cities = client.get_cities()

    # 2. Собираем все уникальные товары из всех городов
    all_products = {}
    product_availability = {}  # В каких городах доступен товар

    for city in cities:
        products = client.get_products(city_id=city["id"])

        for product in products:
            product_id = product["id"]

            # Сохраняем информацию о товаре
            if product_id not in all_products:
                all_products[product_id] = {
                    "id": product_id,
                    "name": product["name"],
                    "description": product.get("description", ""),
                    "price": product["price"],
                    "image": product.get("image")
                }
                product_availability[product_id] = []

            # Добавляем город в список доступности
            product_availability[product_id].append({
                "city_id": city["id"],
                "city_name": city["name"],
                "in_stock": product.get("in_stock", True)
            })

    # 3. Формируем итоговый каталог
    catalog = []
    for product_id, product_info in all_products.items():
        catalog.append({
            **product_info,
            "available_in": product_availability[product_id],
            "cities_count": len(product_availability[product_id])
        })

    # Сортируем по популярности (количеству городов)
    catalog.sort(key=lambda x: x["cities_count"], reverse=True)

    return catalog

# Использование
catalog = build_catalog_by_product_type()
for product in catalog[:3]:
    print(f"{product['name']}: доступен в {product['cities_count']} городах")
```

**Пример ответа структуры:**
```json
[
    {
        "id": 101,
        "name": "Товар Премиум",
        "description": "Высококачественный товар",
        "price": 5000.0,
        "image": "https://cdn.example.com/products/101.jpg",
        "available_in": [
            {"city_id": 1, "city_name": "Москва", "in_stock": true},
            {"city_id": 2, "city_name": "Санкт-Петербург", "in_stock": true},
            {"city_id": 3, "city_name": "Казань", "in_stock": false}
        ],
        "cities_count": 3
    }
]
```

---

### 3. Работа с подрайонами

API поддерживает иерархию районов и подрайонов. Ключевые поля:
- `parent_id` - `null` для районов верхнего уровня, ID родительского района для подрайонов
- `sublocations` - массив подрайонов `[{id, title}]` (только для районов верхнего уровня)

#### Построение иерархии город → район → подрайон

```python
def build_location_tree(client):
    """Построение полного дерева локаций: город → район → подрайон"""
    cities = client.get_cities()
    tree = {}

    for city in cities:
        city_id = city["id"]
        locations = client.get_locations(city_id=city_id)

        # Фильтруем только районы верхнего уровня (parent_id = null)
        districts = [loc for loc in locations if loc.get("parent_id") is None]

        tree[city["name"]] = {
            "city_id": city_id,
            "districts": []
        }

        for district in districts:
            district_data = {
                "id": district["id"],
                "name": district["title"],
                "subdistricts": district.get("sublocations", [])
            }
            tree[city["name"]]["districts"].append(district_data)

    return tree

# Использование
tree = build_location_tree(client)

# Вывод иерархии
for city_name, data in tree.items():
    print(f"Город: {city_name}")
    for district in data["districts"]:
        print(f"  Район: {district['name']}")
        for sub in district["subdistricts"]:
            print(f"    - {sub['title']}")
```

**Пример вывода:**
```
Город: Москва
  Район: Центральный район
    - Арбат
    - Тверская
  Район: Северный район
    - Речной вокзал
    - Водный стадион
```

#### Получение товаров в конкретном подрайоне

```python
def get_products_in_subdistrict(client, city_id, subdistrict_id):
    """
    Получение товаров, доступных в конкретном подрайоне.

    Args:
        client: MerchantApiClient
        city_id: ID города
        subdistrict_id: ID подрайона

    Returns:
        Список товаров с ценами и ссылками
    """
    products = client.get_products(city_id=city_id)

    result = []
    for product in products:
        # Проверяем, есть ли подрайон среди локаций товара
        for location in product.get("locations", []):
            if location["pk"] == subdistrict_id:
                result.append({
                    "id": product["pk"],
                    "name": product["full_title"],
                    "price": product["amount"],
                    "old_price": product.get("old_amount"),
                    "link": location.get("link_to_bot", "")
                })
                break

    return result

# Получаем товары в подрайоне "Арбат" (id=211)
products = get_products_in_subdistrict(client, city_id=1, subdistrict_id=211)
for p in products:
    print(f"{p['name']} - {p['price']} RUB")
```

**Ответ:**
```json
[
    {
        "id": 101,
        "name": "Товар Премиум 1г",
        "price": 5000,
        "old_price": 5500,
        "link": "?start=buy_101_211"
    }
]
```

#### Создание адресов с указанием подрайона

```python
# Получаем справочные данные для определения ID подрайонов
reference = client.get_address_reference()

# Находим подрайоны в справочнике (parent_id != null)
print("Доступные подрайоны:")
for city in reference["cities"]:
    print(f"\n{city['title']}:")
    for location in city["locations"]:
        if location["parent_id"] is not None:
            print(f"  - {location['title']} (id={location['id']})")

# Создаем адреса в подрайоне
result = client.create_addresses(
    worker_id=1,
    kind_id=101,
    location_id=211,  # ID подрайона "Арбат"
    texts=[
        "ул. Арбат, д. 10, подъезд 2",
        "ул. Арбат, д. 25, около магазина",
        "Арбатская площадь, за памятником"
    ],
    address_type="pickup"
)

print(f"Создано адресов: {result['created']}")
print(f"Ошибок: {result['failed']}")
```

**Ответ сервера:**
```json
{
    "result": "success",
    "created": 3,
    "failed": 0,
    "addresses": [
        {"id": 10001, "text": "ул. Арбат, д. 10, подъезд 2"},
        {"id": 10002, "text": "ул. Арбат, д. 25, около магазина"},
        {"id": 10003, "text": "Арбатская площадь, за памятником"}
    ],
    "errors": []
}
```

#### Полный пример: витрина с выбором подрайона

```python
def build_catalog_with_subdistricts(client, city_id):
    """
    Построение каталога товаров с группировкой по подрайонам.
    Возвращает структуру для отображения: район -> подрайон -> товары
    """
    locations = client.get_locations(city_id=city_id)
    products = client.get_products(city_id=city_id)

    # Индексируем товары по location_id
    products_by_location = {}
    for product in products:
        for loc in product.get("locations", []):
            loc_id = loc["pk"]
            if loc_id not in products_by_location:
                products_by_location[loc_id] = []
            products_by_location[loc_id].append({
                "id": product["pk"],
                "name": product["full_title"],
                "price": product["amount"],
                "link": loc.get("link_to_bot", "")
            })

    # Строим иерархию
    catalog = []
    districts = [loc for loc in locations if loc.get("parent_id") is None]

    for district in districts:
        district_entry = {
            "id": district["id"],
            "name": district["title"],
            "subdistricts": []
        }

        for sub in district.get("sublocations", []):
            sub_id = sub["id"]
            district_entry["subdistricts"].append({
                "id": sub_id,
                "name": sub["title"],
                "products": products_by_location.get(sub_id, []),
                "products_count": len(products_by_location.get(sub_id, []))
            })

        # Если нет подрайонов, товары привязаны напрямую к району
        if not district_entry["subdistricts"]:
            district_entry["products"] = products_by_location.get(district["id"], [])
            district_entry["products_count"] = len(district_entry["products"])

        catalog.append(district_entry)

    return catalog

# Использование
catalog = build_catalog_with_subdistricts(client, city_id=1)

for district in catalog:
    print(f"\n{district['name']}:")
    for sub in district.get("subdistricts", []):
        print(f"  {sub['name']} ({sub['products_count']} товаров)")
        for p in sub["products"][:2]:  # Первые 2 товара
            print(f"    - {p['name']}: {p['price']} RUB")
```

---

### 4. Работа с отзывами

#### Получение всех отзывов с пагинацией

```python
# Получаем первую страницу отзывов
reviews = client.get_reviews(page=1)
print(reviews)
```

**Ответ сервера:**
```json
{
    "count": 4521,
    "next": "https://api.example.com/api/v1/merchant/reviews/?page=2",
    "previous": null,
    "results": [
        {
            "id": 9001,
            "rate": 5,
            "text": "Отличный магазин! Быстрая доставка, качественный товар.",
            "product_name": "Товар Премиум",
            "city_name": "Москва",
            "created_at": "2026-01-10T14:30:00Z",
            "has_photo": true
        },
        {
            "id": 9000,
            "rate": 5,
            "text": "Все супер, рекомендую!",
            "product_name": "Товар Стандарт",
            "city_name": "Санкт-Петербург",
            "created_at": "2026-01-10T12:15:00Z",
            "has_photo": false
        },
        {
            "id": 8999,
            "rate": 4,
            "text": "Хороший товар, но доставка немного задержалась.",
            "product_name": "Товар Эконом",
            "city_name": "Казань",
            "created_at": "2026-01-10T10:45:00Z",
            "has_photo": false
        }
    ]
}
```

#### Фильтрация отзывов по товару

```python
# Отзывы только на конкретный товар (kind_id)
reviews = client.get_reviews(kind_id=101, page=1)
```

**Ответ сервера:**
```json
{
    "count": 856,
    "next": "https://api.example.com/api/v1/merchant/reviews/?kind_id=101&page=2",
    "previous": null,
    "results": [
        {
            "id": 8950,
            "rate": 5,
            "text": "Товар Премиум - лучший выбор!",
            "product_name": "Товар Премиум",
            "city_name": "Москва",
            "created_at": "2026-01-09T18:20:00Z",
            "has_photo": true
        }
    ]
}
```

#### Фильтрация по минимальному рейтингу

```python
# Только отзывы с рейтингом 4 и выше
reviews = client.get_reviews(min_rate=4, page=1)
```

**Ответ сервера:**
```json
{
    "count": 4102,
    "results": [
        {"id": 9001, "rate": 5, "text": "..."},
        {"id": 9000, "rate": 5, "text": "..."},
        {"id": 8999, "rate": 4, "text": "..."}
    ]
}
```

#### Комбинированная фильтрация

```python
# Отзывы на товар с id=101, рейтинг 5 звезд
reviews = client.get_reviews(kind_id=101, min_rate=5, page=1)
```

#### Полный пример: виджет отзывов

```python
def get_reviews_widget(product_id=None, min_rating=None, limit=5):
    """
    Получение отзывов для виджета на сайте

    Args:
        product_id: ID товара (None = все товары)
        min_rating: Минимальный рейтинг (1-5)
        limit: Количество отзывов для отображения
    """
    reviews_data = client.get_reviews(
        kind_id=product_id,
        min_rate=min_rating,
        page=1
    )

    reviews = reviews_data.get("results", [])[:limit]

    return {
        "total_count": reviews_data.get("count", 0),
        "reviews": [
            {
                "rating": r["rate"],
                "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                "product": r["product_name"],
                "city": r["city_name"],
                "date": r["created_at"][:10],  # Только дата
                "has_photo": r["has_photo"]
            }
            for r in reviews
        ],
        "has_more": reviews_data.get("next") is not None
    }

# Использование
widget = get_reviews_widget(min_rating=4, limit=3)
print(f"Всего отзывов: {widget['total_count']}")
for review in widget["reviews"]:
    print(f"{'⭐' * review['rating']} - {review['text']}")
```

---

### 5. Лента новостей магазина

```python
# Получаем ленту новостей
feed = client.get_feed(page=1)
print(feed)
```

**Ответ сервера:**
```json
{
    "count": 156,
    "next": "https://api.example.com/api/v1/merchant/feed/?page=2",
    "results": [
        {
            "id": 501,
            "kind": "news",
            "title": "Новогодняя акция!",
            "text": "С 1 по 15 января скидка 20% на все товары!",
            "image": "https://cdn.example.com/feed/501.jpg",
            "created_at": "2026-01-01T00:00:00Z"
        },
        {
            "id": 500,
            "kind": "product",
            "title": "Новый товар в каталоге",
            "text": "Встречайте: Товар Ультра Премиум!",
            "image": "https://cdn.example.com/feed/500.jpg",
            "created_at": "2025-12-28T12:00:00Z"
        }
    ]
}
```

#### Фильтрация ленты по типу

```python
# Только новости
news = client.get_feed(kind="news", page=1)

# Только обновления товаров
product_updates = client.get_feed(kind="product", page=1)
```

#### Подгрузка старых записей (infinite scroll)

```python
def load_feed_after(last_id):
    """Загрузить записи ленты после указанного ID"""
    return client.get_feed(after_pk=last_id, page=1)

# Первая загрузка
feed = client.get_feed(page=1)
last_item_id = feed["results"][-1]["id"]

# Подгрузка при скролле
more_items = load_feed_after(last_item_id)
```

---

### 6. Акции и промокоды

```python
# Получаем активные акции
promotions = client.get_promotions()
print(promotions)
```

**Ответ сервера:**
```json
[
    {
        "id": 301,
        "title": "Скидка 10% новым клиентам",
        "description": "Используйте промокод WELCOME при первом заказе",
        "discount_percent": 10,
        "promocode": "WELCOME",
        "valid_until": "2026-12-31T23:59:59Z",
        "min_order_amount": 1000.0,
        "is_active": true
    },
    {
        "id": 302,
        "title": "Бонус за отзыв",
        "description": "Оставьте отзыв и получите 500 RUB на баланс",
        "bonus_amount": 500.0,
        "is_active": true
    }
]
```

---

### 7. Работа с предзаказами

```python
# Получаем информацию о предзаказах
preorders = client.get_preorders()
print(preorders)
```

**Ответ сервера:**
```json
{
    "enabled": true,
    "description": "Предзаказ доступен для товаров, которых нет в наличии",
    "min_amount": 5000.0,
    "max_amount": 100000.0,
    "processing_time": "24-48 часов",
    "available_products": [
        {"id": 105, "name": "Товар Эксклюзив", "preorder_price": 15000.0}
    ]
}
```

---

### 8. Создание счёта на оплату

```python
# Создаём счёт на оплату
invoice = client.create_invoice(
    external_id="ORDER-12345",      # Ваш внутренний ID заказа
    payment_type="card_rub",         # Способ оплаты
    amount=5000.0,                   # Сумма
    currency="RUB",                  # Валюта
    by_webhook=True                  # Получить результат через webhook
)
print(invoice)
```

**Ответ сервера:**
```json
{
    "id": 78901,
    "external_id": "ORDER-12345",
    "payment_type": "card_rub",
    "amount": 5000.0,
    "currency": "RUB",
    "status": "pending",
    "credentials": "4276 **** **** 1234",
    "payment_amount": 5000.0,
    "expires_at": "2026-01-10T15:30:00Z",
    "created_at": "2026-01-10T14:30:00Z"
}
```

---

### 9. Поиск клиентов и управление балансом

```python
# Поиск клиента по username или ID
clients = client.search_clients(query="@username", limit=10)
print(clients)
```

**Ответ сервера:**
```json
[
    {
        "id": 55001,
        "username": "username",
        "first_name": "Иван",
        "balance": 2500.0,
        "orders_count": 15,
        "registered_at": "2025-06-15T10:00:00Z"
    }
]
```

```python
# Изменение баланса клиента
result = client.change_client_balance(
    client_id=55001,
    amount=500.0,          # Положительное = пополнение, отрицательное = списание
    comment="Бонус за отзыв"
)
print(result)
```

**Ответ сервера:**
```json
{
    "success": true,
    "client_id": 55001,
    "old_balance": 2500.0,
    "new_balance": 3000.0,
    "change": 500.0,
    "comment": "Бонус за отзыв"
}
```

---

### 10. Загрузка фотографий

```python
# Загрузка одного фото
with open("photo.jpg", "rb") as f:
    result = client.upload_photos([f])
print(result)
```

**Ответ сервера:**
```json
{
    "success": true,
    "uploaded": [
        {
            "id": "photo_abc123",
            "url": "https://cdn.example.com/uploads/photo_abc123.jpg",
            "thumbnail": "https://cdn.example.com/uploads/thumb_photo_abc123.jpg"
        }
    ]
}
```

---

### 11. Справочные данные для адресов

```python
# Получаем справочные данные для создания адресов
reference = client.get_address_reference()
print(reference)
```

**Ответ сервера:**
```json
{
    "cities": [
        {"id": 1, "name": "Москва"},
        {"id": 2, "name": "Санкт-Петербург"}
    ],
    "products": [
        {"id": 101, "name": "Товар Премиум"},
        {"id": 102, "name": "Товар Стандарт"}
    ],
    "location_types": ["district", "subway", "area"]
}
```

---

### 12. Массовое создание адресов

```python
# Создание нескольких адресов
result = client.create_addresses(
    city_id=1,
    product_id=101,
    addresses=[
        {
            "location_id": 211,
            "coordinates": "55.7558, 37.6173",
            "description": "Рядом с метро Арбатская"
        },
        {
            "location_id": 212,
            "coordinates": "55.7650, 37.6050",
            "description": "Тверская улица"
        }
    ]
)
print(result)
```

**Ответ сервера:**
```json
{
    "success": true,
    "created": 2,
    "addresses": [
        {"id": 10001, "location": "Арбат", "status": "active"},
        {"id": 10002, "location": "Тверская", "status": "active"}
    ]
}
```

---

## Обработка Webhook

Webhook отправляется при изменении статуса заявки на депозит (назначение реквизитов).

```python
from merchant_api import WebhookHandler
from flask import Flask, request

app = Flask(__name__)
handler = WebhookHandler("your-api-secret")

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Webhook-Signature", "")
    data = handler.process_webhook(request.data, signature)

    if data is None:
        return "Invalid signature", 403

    # Обработка результата
    result = data.get("result")
    invoice_id = data.get("pk")
    external_id = data.get("external_id")

    if result == "success":
        # Реквизиты успешно назначены
        credentials = data.get("credentials")
        print(f"Заявка {invoice_id} ({external_id}): реквизиты назначены - {credentials}")
        # Показать реквизиты пользователю для оплаты

    elif result == "error":
        # Не удалось назначить реквизиты
        error_text = data.get("text")
        print(f"Заявка {invoice_id}: ошибка - {error_text}")
        # Предложить пользователю попробовать позже

    elif result == "canceled":
        # Заявка отменена
        print(f"Заявка {invoice_id}: отменена")

    elif result == "expired":
        # Заявка просрочена
        print(f"Заявка {invoice_id}: истекла")

    return "OK", 200
```

**Формат webhook payload:**
```json
{
    "pk": 78901,
    "external_id": "ORDER-12345",
    "payment_type": "card_rub",
    "payment_amount": 5000.0,
    "amount": 5000.0,
    "currency": "RUB",
    "credentials": "4276 **** **** 1234",
    "status": "waiting_at",
    "result": "success",
    "text": "Реквизиты успешно назначены для заявки 78901"
}
```

**Возможные значения `result`:**
| Значение | Описание |
|----------|----------|
| `success` | Реквизиты успешно назначены, поле `credentials` содержит данные для оплаты |
| `error` | Не удалось назначить реквизиты (нет доступных), поле `text` содержит описание |
| `canceled` | Заявка была отменена |
| `expired` | Заявка просрочена (истёк срок ожидания) |

**Возможные значения `status` (статус заявки):**
| Значение | Описание |
|----------|----------|
| `created` | Заявка создана |
| `creds_at` | Ожидает назначения реквизитов |
| `manual_creds_at` | Ожидает ручного ввода реквизитов |
| `waiting_at` | Ожидает оплаты (реквизиты назначены) |
| `payed_at` | Оплачено клиентом (ожидает подтверждения) |
| `done_at` | Заявка выполнена успешно |
| `trouble_at` | Проблемная заявка |
| `expired_at` | Заявка просрочена |
| `canceled_at` | Заявка отменена |

---

## Обработка ошибок

```python
from merchant_api import MerchantApiClient
from merchant_api.exceptions import (
    MerchantApiError,
    AuthenticationError,
    RateLimitError,
    NotFoundError
)

client = MerchantApiClient(...)

try:
    merchant = client.get_merchant()
except AuthenticationError:
    print("Неверный API ключ")
except RateLimitError as e:
    print(f"Превышен лимит запросов. Повторите через {e.retry_after} сек.")
except NotFoundError:
    print("Ресурс не найден")
except MerchantApiError as e:
    print(f"Ошибка API: {e.message}")
```

---

## Rate Limits

### Merchant API (для интеграций)

| Тип запроса | Лимит |
|-------------|-------|
| Общие запросы | 10 req/s, 200 req/min |
| Создание счетов | 3 req/s, 50 req/min |
| Создание адресов | 1 req/s |

### Web Client API (для веб-сайта магазина)

| Операция | Лимит | Действие при превышении |
|----------|-------|-------------------------|
| Регистрация клиентов | 50/мин, 300/час | Автоматическая блокировка регистрации на 24 часа |
| Авторизация клиентов | 30/мин, 200/час | Временная блокировка попыток входа |
| Общие запросы клиента | 20 req/s, 300 req/min | HTTP 429 Too Many Requests |

---

## ⚠️ Требования безопасности для Web Client API

При использовании Web Client API (endpoints `/api/v1/client/*`) **ОБЯЗАТЕЛЬНО** реализуйте на стороне вашего фронтенда:

### 1. Защита от множественной регистрации

Необходимо отслеживать и блокировать повторные регистрации с одинаковых:
- **IP-адреса** - блокировка на 10-30 минут
- **User-Agent** - блокировка подозрительных комбинаций
- **Fingerprint браузера** - использование canvas fingerprint, WebGL fingerprint и др.

**Пример реализации:**
```python
import hashlib
from django.core.cache import cache

def check_registration_allowed(ip: str, user_agent: str, block_minutes: int = 10) -> bool:
    """Проверка возможности регистрации с данного IP/User-Agent."""
    fingerprint = hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()
    cache_key = f"reg_block:{fingerprint}"

    if cache.get(cache_key):
        return False  # Заблокировано

    return True

def record_registration(ip: str, user_agent: str, block_minutes: int = 10):
    """Записать факт регистрации для блокировки повторных."""
    fingerprint = hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()
    cache_key = f"reg_block:{fingerprint}"
    cache.set(cache_key, True, block_minutes * 60)
```

### 2. Защита от брутфорса авторизации

При авторизации клиента по auth_code необходимо:
- **Ограничивать попытки по IP** - не более 3-5 попыток в минуту с одного IP
- **Использовать captcha** - обязательно при каждой попытке входа
- **Логировать подозрительную активность** - множественные неудачные попытки

**Пример реализации:**
```python
def check_login_allowed(ip: str, max_attempts: int = 5, window_minutes: int = 1) -> bool:
    """Проверка возможности попытки входа с данного IP."""
    cache_key = f"login_attempts:{ip}"
    attempts = cache.get(cache_key, 0)

    if attempts >= max_attempts:
        return False  # Слишком много попыток

    cache.set(cache_key, attempts + 1, window_minutes * 60)
    return True
```

### 3. Важно!

- API лимиты на стороне сервера являются **последней линией защиты**
- Основная защита должна быть реализована на **вашем фронтенде**
- При достижении серверных лимитов **регистрация для всего магазина блокируется на 24 часа**
- Рекомендуется использовать **WAF** (Web Application Firewall) для дополнительной защиты

---

## Версия SDK: 1.1.0
