"""Merchant API SDK - Client with TOR proxy support"""

import requests
from typing import Optional, List, Dict, Any, BinaryIO
from urllib.parse import urljoin

from .exceptions import (
    MerchantApiError, AuthenticationError, RateLimitError,
    ValidationError, NotFoundError, ServerError, TorConnectionError
)


class MerchantApiClient:
    """
    Client for Merchant API with TOR proxy support.

    Args:
        base_url: API base URL
        api_key: Your API key
        api_secret: Your API secret
        use_tor: Use TOR proxy (default: True, recommended)
        tor_proxy: TOR SOCKS5 proxy URL (default: socks5h://127.0.0.1:9050)
        timeout: Request timeout in seconds (default: 30)
    """

    DEFAULT_TOR_PROXY = "socks5h://127.0.0.1:9050"

    def __init__(self, base_url: str, api_key: str, api_secret: str,
                 use_tor: bool = True, tor_proxy: str = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.use_tor = use_tor
        self.tor_proxy = tor_proxy or self.DEFAULT_TOR_PROXY
        self.timeout = timeout
        self._session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        if self.use_tor:
            session.proxies = {"http": self.tor_proxy, "https": self.tor_proxy}
        return session

    def _request(self, method, endpoint, params=None, json_data=None, files=None):
        url = urljoin(self.base_url, f"/api/v1/{endpoint.lstrip('/')}")
        try:
            if files:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                resp = self._session.request(method, url, params=params, files=files,
                                             headers=headers, timeout=self.timeout)
            else:
                resp = self._session.request(method, url, params=params, json=json_data,
                                             timeout=self.timeout)
        except requests.exceptions.ProxyError as e:
            raise TorConnectionError(f"TOR proxy connection failed: {e}")
        except requests.exceptions.RequestException as e:
            raise MerchantApiError(f"Request failed: {e}")

        return self._handle_response(resp)

    def _handle_response(self, resp):
        try:
            data = resp.json()
        except ValueError:
            data = {"text": resp.text}

        if resp.status_code in (200, 201, 202, 206):
            return data
        elif resp.status_code == 400:
            raise ValidationError(data.get("text") or "Validation error", status_code=400,
                                  response=data, errors=data.get("errors", {}))
        elif resp.status_code in (401, 403):
            raise AuthenticationError(data.get("text") or "Auth failed", status_code=resp.status_code)
        elif resp.status_code == 404:
            raise NotFoundError(data.get("text") or "Not found", status_code=404)
        elif resp.status_code == 429:
            raise RateLimitError(data.get("text") or "Rate limit", status_code=429,
                                 retry_after=resp.headers.get("Retry-After"))
        elif resp.status_code >= 500:
            raise ServerError(data.get("text") or "Server error", status_code=resp.status_code)
        raise MerchantApiError(data.get("text") or "Error", status_code=resp.status_code)

    # API Methods

    def get_merchant(self) -> Dict[str, Any]:
        """
        Получение информации о магазине.

        Returns:
            Dict со структурой:
            {
                "pk": int,                    # ID магазина
                "avatar": str | None,         # URL аватара
                "title": str,                 # Название магазина
                "description": str,           # Описание
                "currency": str,              # Код валюты (RUB, USD и т.д.)
                "in_working": bool,           # Магазин работает
                "purchase_count": int,        # Количество покупок
                "channel_text": str,          # Текст канала
                "channel_link": str,          # Ссылка на канал
                "site_text": str,             # Текст сайта
                "site_link": str,             # Ссылка на сайт
                "site1_text": str,            # Доп. сайт 1 текст
                "site1_link": str,            # Доп. сайт 1 ссылка
                "site2_text": str,            # Доп. сайт 2 текст
                "site2_link": str,            # Доп. сайт 2 ссылка
                "referal_is_acive": bool,     # Реферальная программа активна
                "need_subscribe_kind": int | None,  # Требуется подписка (тип)
                "chats_to_subscribe": [       # Чаты для подписки
                    {
                        "title": str,         # Название чата
                        "is_active": bool,    # Активен
                        "link_to_invite": str # Ссылка для вступления
                    }
                ],
                "global_values": dict,        # Глобальные переменные магазина
                "bot_link": str,              # Ссылка на бота
                "info_texts": [               # Информационные тексты
                    {
                        "lang_code": str,     # Код языка (ru, en)
                        "lang": int,          # ID языка
                        "slug": str,          # Идентификатор текста
                        "text": str           # Содержимое
                    }
                ]
            }

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> merchant = client.get_merchant()
            >>> print(merchant['title'])
            'Мой магазин'
        """
        return self._request("GET", "merchant/")

    def get_cities(self) -> List[Dict[str, Any]]:
        """
        Получение списка городов магазина.

        Returns:
            List[Dict] со структурой каждого города:
            {
                "pk": int,                # ID города
                "title": str,             # Название города
                "published": bool,        # Опубликован
                "preorder_published": bool, # Предзаказы опубликованы
                "order": int,             # Порядок сортировки
                "avatar_url": str | None  # URL аватара города
            }

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> cities = client.get_cities()
            >>> for city in cities:
            ...     print(f"{city['title']} (ID: {city['pk']})")
        """
        return self._request("GET", "merchant/cities/")

    def get_products(self, city_id: int) -> List[Dict[str, Any]]:
        """
        Получение товаров города с районами и типами адресов.

        Args:
            city_id: ID города

        Returns:
            List[Dict] со структурой каждого товара:
            {
                "pk": int,                # ID товара
                "group": {                # Группа товара
                    "pk": int,
                    "title": str,
                    "avatar": str | None,
                    "description": str,
                    "order": int
                } | None,
                "avatar": str | None,     # URL аватара
                "title": str,             # Название
                "full_title": str,        # Полное название (группа + название)
                "description": str,       # Описание
                "amount": float,          # Цена
                "old_amount": float | None, # Старая цена (для скидок)
                "city_prices": [          # Цены по городам
                    {
                        "city_id": int,
                        "amount": float,
                        "old_amount": float | None,
                        "lucky_price": float | None
                    }
                ],
                "is_available": bool,     # Доступен
                "is_preorder": bool,      # Предзаказ
                "order": int,             # Порядок сортировки
                "locations": [            # Районы с доступными типами адресов
                    {
                        "pk": int,
                        "title": str,
                        "available_address_types": [  # Типы для этого района
                            {
                                "code": str,      # "" = "Не указан", "klad", "magnit"
                                "name": str,      # Название типа
                                "charge": int     # Наценка
                            }
                        ]
                    }
                ],
                "lucky_enabled": bool,    # Счастливая цена включена
                "lucky_hours": str,       # Часы счастливой цены (напр. "2,4")
                "lucky_price": float | None, # Счастливая цена
                "dop_text": str,          # Дополнительный текст
                "dop_link": str,          # Дополнительная ссылка
                "link_to_bot": str,       # Параметр ссылки для бота
                "no_discount": bool       # Скидки не применяются
            }

        Raises:
            AuthenticationError: Неверный API ключ
            NotFoundError: Город не найден
            RateLimitError: Превышен лимит запросов

        Example:
            >>> products = client.get_products(city_id=1)
            >>> for p in products:
            ...     print(f"{p['full_title']}: {p['amount']} руб.")
        """
        return self._request("GET", f"merchant/cities/{city_id}/products/")

    def get_locations(self, city_id: int) -> List[Dict[str, Any]]:
        """
        Получение районов города с товарами.

        Args:
            city_id: ID города

        Returns:
            List[Dict] со структурой каждого района:
            {
                "pk": int,                # ID района
                "city": {                 # Город
                    "pk": int,
                    "title": str,
                    "published": bool,
                    "preorder_published": bool,
                    "order": int,
                    "avatar_url": str | None
                },
                "title": str,             # Название района
                "published": bool,        # Опубликован
                "order": int,             # Порядок сортировки
                "kinds": [...],           # Товары района (см. get_products)
                "link_to_bot": str,       # Параметр ссылки для бота
                "parent": {               # Родительский район
                    "pk": int,
                    "title": str
                } | None,
                "parent_id": int | None,  # ID родительского района
                "sublocations": [         # Подрайоны
                    {
                        "id": int,
                        "title": str
                    }
                ]
            }

        Raises:
            AuthenticationError: Неверный API ключ
            NotFoundError: Город не найден
            RateLimitError: Превышен лимит запросов

        Example:
            >>> locations = client.get_locations(city_id=1)
            >>> for loc in locations:
            ...     print(f"{loc['title']}: {len(loc['kinds'])} товаров")
        """
        return self._request("GET", f"merchant/cities/{city_id}/locations/")

    def get_promotions(self) -> List[Dict[str, Any]]:
        """
        Получение списка акций магазина.

        Returns:
            List[Dict] со структурой каждой акции:
            {
                "pk": int,                # ID акции
                "kind": int,              # Тип акции (1-10)
                "start": str | None,      # Дата начала ISO 8601
                "end": str | None,        # Дата окончания ISO 8601
                "name": str,              # Название
                "description": str,       # Описание
                "extra_params": dict | str, # Дополнительные параметры (зависит от типа)
                "kinds": [                # Товары в акции
                    {
                        "pk": int,
                        "avatar": str | None,
                        "full_title": str,
                        "old_amount": float | None,
                        "amount": float
                    }
                ]
            }

            Типы акций (kind):
            - 1: KIND_CNT - Скидка за N покупок
            - 2: KIND_DEP - Скидка за пополнение
            - 3: KIND_DEP_ONE_TIME - Одноразовая скидка за пополнение
            - 4: KIND_REVIEW - Скидка за отзыв
            - 5: KIND_ALL_DISCOUNT - Общая скидка на все товары
            - 6: KIND_NEXT_BUY - Скидка на следующую покупку
            - 7: KIND_PRIVATE_ROLL - Приватный розыгрыш

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> promos = client.get_promotions()
            >>> for p in promos:
            ...     print(f"{p['name']}: {p['description']}")
        """
        return self._request("GET", "merchant/promo/")

    def get_preorders(self) -> List[Dict[str, Any]]:
        """
        Получение каталога предзаказов по городам.

        Returns:
            List[Dict] со структурой каждого города:
            {
                "pk": int,                # ID города
                "title": str,             # Название города
                "preorder_published": bool, # Предзаказы опубликованы
                "order": int,             # Порядок сортировки
                "products": [             # Товары для предзаказа
                    {
                        "pk": int,
                        "group": {...} | None,
                        "avatar": str | None,
                        "title": str,
                        "full_title": str,
                        "description": str,
                        "amount": float,
                        "old_amount": float | None,
                        "is_available": bool,
                        "is_preorder": bool,
                        "preorder_text": str, # Текст предзаказа
                        "order": int,
                        "locations": [        # Районы для предзаказа
                            {
                                "pk": int,
                                "title": str,
                                "published": bool,
                                "order": int,
                                "link_to_bot": str,
                                "fullbot_link": str,  # Полная ссылка на бота
                                "parent": {...} | None,
                                "parent_id": int | None,
                                "sublocations": [
                                    {
                                        "id": int,
                                        "title": str,
                                        "link_to_bot": str,
                                        "fullbot_link": str
                                    }
                                ]
                            }
                        ],
                        "fullbot_link": str,
                        "no_discount": bool
                    }
                ],
                "fullbot_link": str,
                "avatar_url": str | None
            }

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> preorders = client.get_preorders()
            >>> for city in preorders:
            ...     print(f"{city['title']}: {len(city['products'])} товаров")
        """
        return self._request("GET", "merchant/preorders/")

    def get_address_reference(self) -> Dict[str, Any]:
        """
        Получение справочных данных для создания адресов.

        Содержит все необходимые ID для метода create_addresses().

        Returns:
            Dict со структурой:
            {
                "merchant": {             # Магазин
                    "id": int,
                    "title": str
                },
                "cities": [               # Города с районами
                    {
                        "id": int,
                        "title": str,
                        "avatar_url": str | None,
                        "locations": [    # Районы города
                            {
                                "id": int,
                                "title": str,
                                "parent_id": int | None
                            }
                        ]
                    }
                ],
                "kinds": [                # Товары
                    {
                        "id": int,
                        "title": str,
                        "group_title": str | None,
                        "amount": float
                    }
                ],
                "address_types": [        # Типы адресов
                    {
                        "code": str,      # Код (klad, magnit, etc.)
                        "name": str       # Название
                    }
                ],
                "workers": [              # Поставщики
                    {
                        "id": int,
                        "title": str
                    }
                ],
                "mks": [                  # Мастер-клады
                    {
                        "id": int,
                        "title": str,
                        "worker_id": int,
                        "worker_title": str
                    }
                ]
            }

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> ref = client.get_address_reference()
            >>> # Найти ID района "Центр" в городе "Москва"
            >>> for city in ref['cities']:
            ...     if city['title'] == 'Москва':
            ...         for loc in city['locations']:
            ...             if loc['title'] == 'Центр':
            ...                 print(f"Location ID: {loc['id']}")
        """
        return self._request("GET", "merchant/addresses/reference/")

    def get_reviews(self, kind_id: int = None, min_rate: int = None, page: int = None) -> Dict[str, Any]:
        """
        Получение отзывов магазина с пагинацией.

        Args:
            kind_id: Фильтр по ID товара (опционально)
            min_rate: Минимальная оценка 1-5 (опционально)
            page: Номер страницы (опционально)

        Returns:
            Dict со структурой:
            {
                "count": int,             # Общее количество отзывов
                "next": str | None,       # URL следующей страницы
                "previous": str | None,   # URL предыдущей страницы
                "results": [              # Список отзывов
                    {
                        "text": str,          # Текст отзыва
                        "rate": int,          # Оценка 1-5
                        "rate_stars": str,    # Звёзды (напр. "★★★★☆")
                        "answer": str | None, # Ответ магазина
                        "created": str,       # Дата создания ISO 8601
                        "client": str,        # Скрытое имя клиента
                        "purchase": {         # Информация о покупке
                            "location": str | None,    # Район
                            "kind": str | None,        # Товар
                            "city": str | None,        # Город
                            "address_type": str | None # Тип адреса
                        } | str
                    }
                ]
            }

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> reviews = client.get_reviews(min_rate=4, page=1)
            >>> for r in reviews['results']:
            ...     print(f"{r['rate_stars']} - {r['text'][:50]}...")
        """
        params = {}
        if kind_id: params["kind_id"] = kind_id
        if min_rate: params["rate__gte"] = min_rate
        if page: params["page"] = page
        return self._request("GET", "merchant/reviews/", params=params)

    def get_feed(self, kind: str = None, after_pk: int = None, page: int = None) -> Dict[str, Any]:
        """
        Получение ленты новостей магазина с пагинацией.

        Args:
            kind: Тип новости (опционально)
            after_pk: Показать новости с ID больше указанного (опционально)
            page: Номер страницы (опционально)

        Returns:
            Dict со структурой:
            {
                "count": int,             # Общее количество новостей
                "next": str | None,       # URL следующей страницы
                "previous": str | None,   # URL предыдущей страницы
                "results": [              # Список новостей
                    {
                        "pk": int,            # ID новости
                        "media": str | None,  # URL медиафайла
                        "title": str,         # Заголовок
                        "text": str,          # Текст новости
                        "kind": str,          # Тип новости
                        "created": str        # Дата создания ISO 8601
                    }
                ]
            }

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов

        Example:
            >>> feed = client.get_feed(page=1)
            >>> for news in feed['results']:
            ...     print(f"[{news['created']}] {news['title']}")
        """
        params = {}
        if kind: params["kind"] = kind
        if after_pk: params["pk__gt"] = after_pk
        if page: params["page"] = page
        return self._request("GET", "merchant/feed/", params=params)

    def create_addresses(self, worker_id: int, kind_id: int, location_id: int,
                         texts: List[str], address_type: str = None,
                         mk_id: int = None) -> Dict[str, Any]:
        """
        Массовое создание адресов (точек).

        Args:
            worker_id: ID поставщика (из get_address_reference)
            kind_id: ID товара (из get_address_reference)
            location_id: ID района (из get_address_reference)
            texts: Список текстов адресов (от 1 до 50, макс. 1000 символов каждый)
            address_type: Тип адреса - код из address_types (опционально)
            mk_id: ID мастер-клада (опционально)

        Returns:
            Dict со структурой:
            {
                "result": "success",
                "created": int,           # Количество созданных адресов
                "failed": int,            # Количество ошибок
                "addresses": [            # Успешно созданные
                    {
                        "id": int,        # ID адреса
                        "text": str       # Текст адреса
                    }
                ],
                "errors": [               # Ошибки создания
                    {
                        "text": str,      # Текст адреса
                        "index": int,     # Индекс в массиве texts
                        "error": str      # Описание ошибки
                    }
                ]
            }

        Raises:
            AuthenticationError: Неверный API ключ
            ValidationError: Ошибка валидации данных
            RateLimitError: Превышен лимит запросов (1 req/s для адресов)

        Example:
            >>> result = client.create_addresses(
            ...     worker_id=1,
            ...     kind_id=5,
            ...     location_id=10,
            ...     texts=["Адрес 1: описание клада", "Адрес 2: описание клада"],
            ...     address_type="klad"
            ... )
            >>> print(f"Создано: {result['created']}, ошибок: {result['failed']}")
        """
        data = {"worker_id": worker_id, "kind_id": kind_id, "location_id": location_id, "texts": texts}
        if address_type: data["address_type"] = address_type
        if mk_id: data["mk_id"] = mk_id
        return self._request("POST", "merchant/addresses/", json_data=data)

    def search_clients(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск клиентов по username, uid или имени.

        Args:
            query: Строка поиска (минимум 2 символа)
            limit: Максимальное количество результатов (по умолчанию 10)

        Returns:
            List[Dict] со структурой каждого клиента:
            {
                "id": int,                # ID клиента
                "uid": str,               # Telegram UID или web_xxx
                "username": str | None,   # Telegram username
                "first_name": str | None, # Имя
                "last_name": str | None,  # Фамилия
                "balance": float,         # Текущий баланс
                "created": str            # Дата регистрации ISO 8601
            }

        Raises:
            AuthenticationError: Неверный API ключ
            ValidationError: Слишком короткий запрос
            RateLimitError: Превышен лимит запросов

        Example:
            >>> clients = client.search_clients("ivan", limit=5)
            >>> for c in clients:
            ...     print(f"@{c['username']}: баланс {c['balance']}")
        """
        return self._request("GET", "merchant/clients/search/", params={"q": query, "limit": limit})

    def change_client_balance(self, client_id: int, new_balance: float,
                              comment: str = None) -> Dict[str, Any]:
        """
        Изменение баланса клиента (асинхронная операция).

        Баланс изменяется через фоновую задачу. Клиент получит уведомление
        в Telegram о изменении баланса.

        Args:
            client_id: ID клиента
            new_balance: Новый баланс (может быть отрицательным для списания)
            comment: Комментарий к операции (опционально)

        Returns:
            Dict со структурой:
            {
                "result": bool,           # Успешно поставлено в очередь
                "client_id": int,         # ID клиента
                "old_balance": float,     # Текущий баланс (до изменения)
                "new_balance": float,     # Запрошенный новый баланс
                "message": str            # Информация о статусе задачи
            }

        Raises:
            AuthenticationError: Неверный API ключ
            NotFoundError: Клиент не найден
            ValidationError: Некорректный баланс
            RateLimitError: Превышен лимит запросов

        Example:
            >>> # Начислить 100 рублей
            >>> result = client.change_client_balance(
            ...     client_id=123,
            ...     new_balance=250.0,  # Было 150, станет 250
            ...     comment="Бонус за отзыв"
            ... )
            >>> print(result['message'])
        """
        data = {"new_balance": new_balance}
        if comment: data["comment"] = comment
        return self._request("POST", f"merchant/clients/{client_id}/balance/", json_data=data)

    def upload_photos(self, photos: List[Any]) -> Dict[str, Any]:
        """
        Загрузка фото на файловый хостинг.

        Ограничения:
            - Максимум 10 файлов за запрос
            - Максимальный размер файла: 5 MB
            - Поддерживаемые форматы: jpg, png, webp
            - Rate limit: 1 запрос в секунду
            - Срок хранения файлов: 90 дней (поле expires_at в ответе)

        Args:
            photos: Список файлов для загрузки. Каждый элемент может быть:
                - tuple (filename, file_object) - файл с именем
                - tuple (filename, file_object, content_type) - файл с именем и MIME типом
                - открытый файловый объект (имя берётся из file.name)

        Returns:
            Dict с результатом загрузки:
                - result: 'success' | 'partial_success' | 'error'
                - uploaded: количество успешно загруженных
                - failed: количество с ошибками
                - photos: список с результатами для каждого файла

        Raises:
            AuthenticationError: API ключ не имеет доступа к загрузке фото
            RateLimitError: Превышен лимит запросов (1/сек)
            ValidationError: Ошибка валидации файлов

        Examples:
            # Загрузка из файлов на диске
            >>> with open('photo1.jpg', 'rb') as f1, open('photo2.jpg', 'rb') as f2:
            ...     result = client.upload_photos([f1, f2])
            >>> print(result)
            {
                'result': 'success',
                'uploaded': 2,
                'failed': 0,
                'photos': [
                    {'index': 0, 'url': 'https://example.com/i/2025/01/abc/photo1.jpg', 'error': None},
                    {'index': 1, 'url': 'https://example.com/i/2025/01/abc/photo2.jpg', 'error': None}
                ]
            }

            # Загрузка с явным указанием имени файла
            >>> with open('photo.jpg', 'rb') as f:
            ...     result = client.upload_photos([('my_photo.jpg', f)])

            # Загрузка из bytes
            >>> image_bytes = download_image_from_url(url)
            >>> result = client.upload_photos([('downloaded.jpg', io.BytesIO(image_bytes))])

            # Обработка частичного успеха
            >>> result = client.upload_photos(photos)
            >>> if result['result'] == 'partial_success':
            ...     for photo in result['photos']:
            ...         if photo['error']:
            ...             print(f"Ошибка #{photo['index']}: {photo['error']}")
            ...         else:
            ...             print(f"Загружено: {photo['url']}")

            # Batch загрузка с проверкой
            >>> urls = []
            >>> for photo in result['photos']:
            ...     if photo['url']:
            ...         urls.append(photo['url'])
            >>> print(f"Загружено {len(urls)} из {len(photos)} фото")
        """
        files = [("photos", photo) for photo in photos]
        return self._request("POST", "merchant/upload/photo/", files=files)

    def create_invoice(self, external_id: str, payment_type: str, amount: float,
                       currency: str = "RUB", by_webhook: bool = True) -> Dict[str, Any]:
        """
        Создание заявки на пополнение баланса клиента.

        Args:
            external_id: ID заявки в вашей системе (уникальный)
            payment_type: Код способа оплаты (CARD, USDT, etc.)
            amount: Сумма к получению в валюте магазина
            currency: Код валюты приема средств (по умолчанию "RUB")
            by_webhook: Получать результат по webhook (требуется callback_url)

        Returns:
            Dict со структурой:
            {
                "pk": int,                # ID заявки в системе
                "external_id": str,       # ID заявки в вашей системе
                "payment_type": str,      # Способ оплаты
                "payment_amount": float,  # Сумма к оплате в валюте оплаты
                "amount": float,          # Сумма к зачислению в валюте магазина
                "currency": str,          # Валюта оплаты
                "credentials": str | None, # Реквизиты для оплаты
                "status": str             # Статус заявки
            }

            Статусы (status):
            - "created": Заявка создана
            - "creds_at": Ожидает назначения реквизитов
            - "manual_creds_at": Ожидает ручного ввода реквизитов
            - "waiting_at": Ожидает оплаты (реквизиты назначены)
            - "payed_at": Оплачено клиентом
            - "done_at": Выполнена успешно
            - "trouble_at": Открыт спор
            - "expired_at": Просрочена
            - "canceled_at": Отменена

        Raises:
            AuthenticationError: Неверный API ключ
            ValidationError: Ошибка валидации (неверный payment_type, amount <= 0)
            RateLimitError: Превышен лимит запросов (3 req/s, 50 req/min)

        Example:
            >>> invoice = client.create_invoice(
            ...     external_id="order_12345",
            ...     payment_type="CARD",
            ...     amount=1000.0,
            ...     currency="RUB",
            ...     by_webhook=True
            ... )
            >>> print(f"Заявка #{invoice['pk']}, оплатить: {invoice['payment_amount']}")
        """
        return self._request("POST", "invoice/", json_data={
            "id": external_id, "payment_type": payment_type,
            "amount": amount, "currency": currency, "by_webhook": by_webhook
        })

    def check_tor_connection(self):
        if not self.use_tor: return False
        try:
            resp = self._session.get("https://check.torproject.org/api/ip", timeout=10)
            return resp.json().get("IsTor", False)
        except: return False

    def set_tor(self, enabled, proxy=None):
        self.use_tor = enabled
        if proxy: self.tor_proxy = proxy
        self._session = self._create_session()
