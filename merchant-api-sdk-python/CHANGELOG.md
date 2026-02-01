# Changelog

All notable changes to the Merchant API SDK will be documented in this file.

## [1.11.1] - 2026-01-27

### Changed
- **Убрана загрузка файлов через сообщения** — методы `sendDepositMessage()` / `sendPurchaseMessage()`
  теперь принимают только текст. Для отправки фото используйте `uploadPhotos()`, получите URL,
  затем вставьте URL в текст сообщения.
- **Статус предзаказа в покупках** — поле `status_display` теперь корректно отображает статус предзаказов:
  - Для предзаказов (`is_preorder=true`) со статусом `"2"` (Выполнена), если оператор ещё не выполнил предзаказ, `status_display` возвращает **"Ожидает выполнения"** вместо "Выполнена"
  - После выполнения предзаказа оператором `status_display` возвращает "Выполнена" как обычно
  - Затрагивает оба endpoint: `getPurchases()` (список) и `getPurchase()` (детали)

### Added
- **Поле `preorder_doned` в деталях покупки** — метод `getPurchase()` теперь возвращает поле `preorder_doned`:
  - `0` — предзаказ ещё не выполнен оператором
  - `> 0` — предзаказ выполнен
  - Для обычных покупок (`is_preorder=false`) всегда `0`

### Response Format

**Предзаказ ожидает выполнения (`getPurchases` / `getPurchase`):**
```json
{
  "data": {
    "pk": 123,
    "status": "2",
    "status_display": "Ожидает выполнения",
    "is_preorder": true,
    "preorder_doned": 0
  }
}
```

**Предзаказ выполнен оператором:**
```json
{
  "data": {
    "pk": 123,
    "status": "2",
    "status_display": "Выполнена",
    "is_preorder": true,
    "preorder_doned": 1
  }
}
```

### Рекомендации для фронтенда

```javascript
// Используйте status_display для отображения — он уже учитывает предзаказы
<span className="status">{purchase.status_display}</span>

// Или проверяйте вручную через preorder_doned (только в деталях покупки)
if (purchase.is_preorder && purchase.status === '2') {
    const isReady = purchase.preorder_doned > 0;
    showStatus(isReady ? 'Выполнена' : 'Ожидает выполнения');
}
```

---

## [1.11.0] - 2026-01-27

### Changed
- **Загрузка фото доступна всем API ключам** — флаг `can_upload_photos` больше не требуется.
  Любой API ключ теперь может использовать метод `uploadPhotos()` / `upload_photos()`.

- **Срок хранения файлов: 90 дней** — загруженные через API фото автоматически удаляются через 90 дней.
  Ответ метода теперь содержит поле `expires_at` с датой истечения для каждого файла.

### Important
- **Для прикрепления фото к покупкам/депозитам используйте метод `uploadPhotos()`** — загрузите фото,
  получите URL, затем отправьте URL в сообщении через `sendPurchaseMessage()` / `sendDepositMessage()`.

## [1.10.3] - 2026-01-21

### Added
- **Количество сообщений в списках** — методы `getPurchases()` и `getDeposits()` теперь возвращают поле `messages_count`:
  - Количество сообщений в чате по заявке/покупке
  - Позволяет реализовать индикатор непрочитанных сообщений на фронтенде

- **Фильтрация новых сообщений поддержки** — метод `getSupportMessages()` теперь поддерживает параметр `after_pk`:
  - `after_pk` — PK последнего известного сообщения, вернутся только более новые
  - При использовании `after_pk` сообщения возвращаются в хронологическом порядке (старые → новые)
  - Без `after_pk` — стандартный порядок (новые первые)

### Response Format

**Список покупок (`getPurchases`):**
```json
{
  "data": [
    {
      "pk": 123,
      "product_title": "Товар",
      "status": "4",
      "messages_count": 5,
      "..."
    }
  ]
}
```

**Список депозитов (`getDeposits`):**
```json
{
  "data": [
    {
      "pk": 456,
      "payment_type": "card_rub",
      "status": "trouble_at",
      "messages_count": 3,
      "..."
    }
  ]
}
```

**Сообщения поддержки с `after_pk`:**
```javascript
// Получить только новые сообщения после pk=100
const newMessages = await client.getSupportMessages({ afterPk: 100 });
// Возвращает сообщения с pk > 100 в хронологическом порядке
```

### Рекомендации для фронтенда: Индикатор новых сообщений

Для отображения индикатора непрочитанных сообщений используйте localStorage:

```javascript
// === Утилиты для работы с кешем сообщений ===

const CACHE_KEY_PREFIX = 'msg_count_';

/**
 * Получает закешированное количество сообщений.
 * @param {string} type - Тип заявки: 'purchase' или 'deposit'
 * @param {number} id - ID заявки
 * @returns {number|null} - Количество из кеша или null если нет
 */
function getCachedMessageCount(type, id) {
    const key = `${CACHE_KEY_PREFIX}${type}_${id}`;
    const cached = localStorage.getItem(key);
    return cached !== null ? parseInt(cached, 10) : null;
}

/**
 * Сохраняет количество сообщений в кеш.
 * Вызывать ТОЛЬКО при открытии чата заявки!
 * @param {string} type - Тип заявки: 'purchase' или 'deposit'
 * @param {number} id - ID заявки
 * @param {number} count - Текущее количество сообщений
 */
function updateCachedMessageCount(type, id, count) {
    const key = `${CACHE_KEY_PREFIX}${type}_${id}`;
    localStorage.setItem(key, count.toString());
}

/**
 * Проверяет, есть ли новые сообщения.
 * @param {string} type - Тип заявки
 * @param {number} id - ID заявки
 * @param {number} currentCount - Текущее количество с сервера
 * @returns {boolean} - true если есть новые сообщения
 */
function hasNewMessages(type, id, currentCount) {
    const cached = getCachedMessageCount(type, id);
    // Если нет в кеше - первое открытие, новых нет
    if (cached === null) return false;
    // Если текущее больше кеша - есть новые
    return currentCount > cached;
}

/**
 * Получает количество новых сообщений.
 * @param {string} type - Тип заявки
 * @param {number} id - ID заявки
 * @param {number} currentCount - Текущее количество с сервера
 * @returns {number} - Количество новых сообщений (0 если нет)
 */
function getNewMessagesCount(type, id, currentCount) {
    const cached = getCachedMessageCount(type, id);
    if (cached === null) return 0;
    return Math.max(0, currentCount - cached);
}
```

```javascript
// === Пример использования в React ===

function PurchaseList() {
    const [purchases, setPurchases] = useState([]);

    useEffect(() => {
        loadPurchases();
    }, []);

    const loadPurchases = async () => {
        const result = await client.getPurchases();
        setPurchases(result.data);
    };

    // При первой загрузке списка - инициализируем кеш для новых заявок
    useEffect(() => {
        purchases.forEach(p => {
            if (getCachedMessageCount('purchase', p.pk) === null) {
                // Первое появление заявки - сохраняем текущее значение
                updateCachedMessageCount('purchase', p.pk, p.messages_count);
            }
        });
    }, [purchases]);

    return (
        <div className="purchase-list">
            {purchases.map(purchase => (
                <PurchaseCard
                    key={purchase.pk}
                    purchase={purchase}
                    hasNew={hasNewMessages('purchase', purchase.pk, purchase.messages_count)}
                    newCount={getNewMessagesCount('purchase', purchase.pk, purchase.messages_count)}
                />
            ))}
        </div>
    );
}

function PurchaseCard({ purchase, hasNew, newCount }) {
    const navigate = useNavigate();

    const handleClick = () => {
        // При переходе в чат - НЕ обновляем кеш здесь!
        // Кеш обновится в компоненте чата после загрузки сообщений
        navigate(`/purchases/${purchase.pk}`);
    };

    return (
        <div className="purchase-card" onClick={handleClick}>
            <div className="title">{purchase.product_title}</div>
            <div className="status">{purchase.status_display}</div>

            {/* Индикатор новых сообщений */}
            {hasNew && (
                <span className="new-messages-badge">
                    {newCount > 0 ? newCount : '•'}
                </span>
            )}
        </div>
    );
}
```

```javascript
// === Компонент чата - обновление кеша при просмотре ===

function PurchaseChat({ purchaseId }) {
    const [purchase, setPurchase] = useState(null);
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        loadPurchaseDetails();
    }, [purchaseId]);

    const loadPurchaseDetails = async () => {
        const result = await client.getPurchase(purchaseId);
        setPurchase(result.data);
        setMessages(result.data.messages_history || []);

        // ВАЖНО: Обновляем кеш при просмотре чата!
        // Теперь пользователь "прочитал" все сообщения
        updateCachedMessageCount('purchase', purchaseId, result.data.messages_history?.length || 0);
    };

    return (
        <div className="chat">
            {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.is_user ? 'user' : 'operator'}`}>
                    {msg.message}
                </div>
            ))}
        </div>
    );
}
```

```css
/* === Стили для индикатора новых сообщений === */

.new-messages-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    background-color: #e74c3c;
    color: white;
    border-radius: 10px;
    font-size: 12px;
    font-weight: bold;
    margin-left: 8px;
}

/* Анимация пульсации для привлечения внимания */
.new-messages-badge {
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); }
}
```

### Алгоритм работы

1. **При первой загрузке списка:**
   - Для каждой заявки проверяем наличие записи в localStorage
   - Если записи нет — сохраняем текущее `messages_count` (заявка "прочитана")
   - Если запись есть — сравниваем с текущим значением

2. **При обновлении списка (polling/refresh):**
   - Сравниваем `messages_count` с закешированным значением
   - Если `messages_count > cached` — показываем индикатор

3. **При переходе в чат заявки:**
   - Загружаем полные данные заявки с `messages_history`
   - Обновляем кеш: `localStorage[key] = messages_history.length`
   - Индикатор исчезнет при следующем обновлении списка

### Usage Examples

**Python:**
```python
# Получить покупки с количеством сообщений
purchases = client.get_purchases()
for p in purchases['data']:
    if p['messages_count'] > 0:
        print(f"Покупка #{p['pk']}: {p['messages_count']} сообщений")

# Получить только новые сообщения поддержки
last_known_pk = 100
new_messages = client.get_support_messages(after_pk=last_known_pk)
for msg in new_messages['data']:
    print(f"Новое сообщение: {msg['text']}")
```

**JavaScript:**
```javascript
// Получить депозиты с количеством сообщений
const deposits = await client.getDeposits();
deposits.data.forEach(d => {
    if (d.messages_count > 0) {
        console.log(`Депозит #${d.pk}: ${d.messages_count} сообщений`);
    }
});

// Получить только новые сообщения поддержки
const lastKnownPk = 100;
const newMessages = await client.getSupportMessages({ afterPk: lastKnownPk });
// newMessages.data содержит только сообщения с pk > 100
```

**PHP:**
```php
// Получить покупки с количеством сообщений
$purchases = $client->getPurchases();
foreach ($purchases['data'] as $p) {
    if ($p['messages_count'] > 0) {
        echo "Покупка #{$p['pk']}: {$p['messages_count']} сообщений\n";
    }
}

// Получить только новые сообщения
$newMessages = $client->getSupportMessages(null, 100); // after_pk=100
```

---

## [1.10.2] - 2026-01-20

### Added
- **Тип адреса в деталях покупки** — метод `getPurchase()` теперь возвращает информацию о типе адреса:
  - `address_type.code` — код типа (например: `magnit`, `tainik`, `pricop`)
  - `address_type.name` — локализованное название из настроек мерчанта (например: "магнит", "тайник")
  - Возвращает `null` если тип адреса не указан

### Response Format

**Детали покупки:**
```json
{
  "data": {
    "pk": 123,
    "address_info": "Адрес клада...",
    "address_type": {
      "code": "magnit",
      "name": "магнит"
    },
    ...
  }
}
```

**Без типа адреса:**
```json
{
  "data": {
    "pk": 123,
    "address_info": "Адрес клада...",
    "address_type": null,
    ...
  }
}
```

---

## [1.10.2a] - 2026-01-20

### Changed
- **BREAKING: `available_address_types` перенесён с уровня товара на уровень района** — теперь для каждого района показываются только те типы адресов, которые реально доступны в этом районе
- **Поддержка точек без типа адреса** — `code: ""` означает "Не указан" (точки без явного типа адреса), такие точки отображаются первыми в списке
- **Убрано поле `extra_worker`** из `available_address_types` — больше не возвращается в API

### Рекомендации по использованию address_type

При выводе списка товаров на сайте/в приложении:

1. **Каждый район имеет свой набор типов адресов.** Поле `available_address_types` теперь находится внутри каждого района (`locations[].available_address_types`), а не на уровне товара.

2. **Для покупки нужен район.** Сначала пользователь выбирает товар, затем район — и только после этого показывайте доступные типы адресов для выбранного района.

3. **Пустой код — это валидный тип.** Если `code: ""`, это означает что тип адреса просто не указан, но покупка полностью доступна.

4. **Наценка за тип.** Поле `charge` указывает дополнительную стоимость за данный тип адреса в валюте магазина.

### Пример использования

```javascript
// Получаем товары города
const products = await client.getProducts(cityId);

for (const product of products) {
  console.log(`${product.title}: ${product.amount} руб.`);

  // Для каждого района показываем доступные типы
  for (const location of product.locations) {
    console.log(`  Район: ${location.title}`);

    for (const addrType of location.available_address_types) {
      const typeName = addrType.code === '' ? 'Обычный' : addrType.name;
      const price = product.amount + addrType.charge;
      console.log(`    - ${typeName}: ${price} руб.`);
    }
  }
}
```

### Response Format

**Товар с районами и типами адресов:**
```json
{
  "pk": 123,
  "title": "Товар",
  "amount": 1000,
  "locations": [
    {
      "pk": 1,
      "title": "Район Центральный",
      "available_address_types": [
        {"code": "", "name": "Не указан", "charge": 0},
        {"code": "magnit", "name": "магнит", "charge": 0}
      ]
    },
    {
      "pk": 2,
      "title": "Район Северный",
      "available_address_types": [
        {"code": "tainik", "name": "тайник", "charge": 50}
      ]
    }
  ]
}
```

---

## [1.10.1] - 2026-01-20

### Changed
- **Скидки клиента** — изменено поведение `getDiscounts()`:
  - По умолчанию возвращает **все** скидки (включая использованные)
  - Добавлен параметр `active=true` для фильтрации только активных (неиспользованных)
  - Добавлено поле `purchase_id` — ID покупки, в которой использована скидка

### Usage Examples

**Python:**
```python
# Все скидки (по умолчанию)
all_discounts = client.get_discounts()

# Только активные (неиспользованные)
active_discounts = client.get_discounts(active=True)
```

**JavaScript:**
```javascript
// Все скидки (по умолчанию)
const allDiscounts = await client.getDiscounts();

// Только активные (неиспользованные)
const activeDiscounts = await client.getDiscounts(null, true);
```

**PHP:**
```php
// Все скидки (по умолчанию)
$allDiscounts = $client->getDiscounts();

// Только активные (неиспользованные)
$activeDiscounts = $client->getDiscounts(null, true);
```

**Go:**
```go
// Все скидки (по умолчанию)
allDiscounts, _ := client.GetDiscounts("", "")

// Только активные (неиспользованные)
activeDiscounts, _ := client.GetDiscounts("", "true")
```

## [1.10.0] - 2026-01-19

### Added
- **Загрузка фото** — новый метод `uploadPhotos()` для загрузки изображений на файловый хостинг:
  - Поддержка batch-загрузки до 10 файлов за запрос
  - Автоматическое удаление EXIF метаданных (GPS, устройство, дата)
  - Конвертация в JPEG формат
  - Rate limit: 1 запрос в секунду
  - **Требуется флаг `can_upload_photos` у API ключа**

### Ограничения
- Максимум 10 файлов за запрос
- Максимальный размер файла: 5 MB
- Поддерживаемые форматы: jpg, png, webp

### Response Format
```json
{
  "result": "success",
  "uploaded": 2,
  "failed": 0,
  "photos": [
    {"index": 0, "url": "https://example.com/i/2026/01/abc/photo1.jpg", "error": null},
    {"index": 1, "url": "https://example.com/i/2026/01/abc/photo2.jpg", "error": null}
  ]
}
```

### Usage Examples

**Python:**
```python
# Загрузка из файлов на диске
with open('photo1.jpg', 'rb') as f1, open('photo2.jpg', 'rb') as f2:
    result = client.upload_photos([f1, f2])

# С указанием имени файла
with open('photo.jpg', 'rb') as f:
    result = client.upload_photos([('my_photo.jpg', f)])

# Из bytes/BytesIO
import io
image_bytes = download_image(url)
result = client.upload_photos([('downloaded.jpg', io.BytesIO(image_bytes))])

# Обработка результата
for photo in result['photos']:
    if photo['url']:
        print(f"Загружено: {photo['url']}")
    else:
        print(f"Ошибка: {photo['error']}")
```

**JavaScript (Node.js):**
```javascript
const fs = require('fs');

// Загрузка из файловой системы
const result = await client.uploadPhotos([
    fs.createReadStream('/path/to/photo1.jpg'),
    fs.createReadStream('/path/to/photo2.jpg')
]);

// Загрузка Buffer с именами
const photo = fs.readFileSync('/path/to/photo.jpg');
const result = await client.uploadPhotos([photo], ['photo.jpg']);

// Обработка результата
result.photos.forEach(p => {
    if (p.url) console.log(`Фото ${p.index}: ${p.url}`);
    else console.error(`Ошибка ${p.index}: ${p.error}`);
});
```

**JavaScript (Browser):**
```javascript
// Из input[type="file"]
const fileInput = document.querySelector('input[type="file"]');
const result = await client.uploadPhotos(Array.from(fileInput.files));
```

**PHP:**
```php
// Загрузка из файловой системы
$result = $client->uploadPhotos([
    '/path/to/photo1.jpg',
    '/path/to/photo2.jpg'
]);

// Из формы ($_FILES)
$photos = [];
foreach ($_FILES['photos']['tmp_name'] as $tmpPath) {
    $photos[] = $tmpPath;
}
$result = $client->uploadPhotos($photos);

// Обработка результата
foreach ($result['photos'] as $photo) {
    if ($photo['url']) {
        echo "Загружено: {$photo['url']}\n";
    } else {
        echo "Ошибка: {$photo['error']}\n";
    }
}
```

### Error Handling

| HTTP Code | Причина |
|-----------|---------|
| 400 | Файлы не предоставлены или неверный формат |
| 403 | API ключ не имеет флага `can_upload_photos` |
| 415 | Неверный Content-Type (должен быть multipart/form-data) |
| 429 | Превышен rate limit (1 запрос/сек) |

**Пример ошибки 415 (неверный Content-Type):**
```json
{
  "result": "error",
  "text": "Неверный Content-Type. Для загрузки файлов используйте multipart/form-data вместо application/json..."
}
```

---

## [1.9.1] - 2026-01-19

### Changed
- **История промокодов** — метод `get_promocodes()` теперь возвращает промокоды обоих форматов (старый и новый):
  - Объединяет данные из `MerchantPromocodeActivation` (новый формат) и `MerchantPromocode` (старый формат)
  - Сортировка по дате активации (новые сверху)
  - Код промокода маскируется: первые 6 символов + `***` + последние 3 символа
  - Формат ответа: `{code, amount, activated_at}`

### Usage Examples

**Python:**
```python
# Получение истории промокодов
history = client.get_promocodes()
for promo in history['data']:
    print(f"{promo['code']}: {promo['amount']} руб. ({promo['activated_at']})")
    # iCode-***0Gy: 100 руб. (2026-01-19T12:00:00Z)
```

---

## [1.9.0] - 2026-01-19

### Added
- **Каталог предзаказов (Preorder Catalog API)** — 3 новых endpoint для работы с предзаказами:
  - `GET /api/v1/client/preorder/cities/` — список городов для предзаказа
  - `GET /api/v1/client/preorder/cities/{city_id}/products/` — товары для предзаказа в городе
  - `GET /api/v1/client/preorder/cities/{city_id}/products/{product_id}/locations/` — районы для предзаказа

- **Сети USDT в методах оплаты** — endpoint `getPaymentMethods()` теперь возвращает доступные сети для USDT.
  - Поле `networks` содержит массив `[{code: "TRON", name: "TRON (TRC-20)"}, ...]`
  - Доступные сети: TRON, ETH, BSC, POLYGON (зависит от настроек мерчанта)

- **Параметр `network` при создании депозита** — метод `createDeposit()` теперь принимает опциональный параметр `network` для USDT.
  - Обязателен при выборе USDT в качестве способа оплаты
  - Возвращает ошибку `NETWORK_REQUIRED` если сеть не указана для USDT

- **Поля `usdt_network` и `usdt_network_display`** — в ответе деталей депозита теперь есть информация о выбранной сети USDT.

- **Пометка ПРОМОКОД в методах оплаты** — способ оплаты `prm` (ПРОМОКОД) теперь содержит:
  - `no_deposit_required: true` — не требует создания заявки на депозит
  - `activation_endpoint: "/api/v1/client/promocodes/activate/"` — endpoint для активации

### Changed
- **Валидация USDT** — при создании депозита с `payment_type=usdt` теперь проверяется:
  - Наличие активных адресов для мерчанта
  - Корректность указанной сети
  - Доступность сети для данного мерчанта

### Usage Examples

**Python:**
```python
# Получение методов оплаты с сетями USDT
methods = client.get_payment_methods()
for method in methods['data']:
    if method['code'] == 'usdt' and 'networks' in method:
        print(f"USDT networks: {method['networks']}")

# Создание депозита с выбором сети USDT
deposit = client.create_deposit(
    payment_type='usdt',
    amount=100,
    network='TRON'  # Обязательно для USDT
)
```

**JavaScript:**
```javascript
// Получение методов оплаты
const methods = await client.getPaymentMethods();
const usdtMethod = methods.data.find(m => m.code === 'usdt');
if (usdtMethod?.networks) {
    console.log('Available USDT networks:', usdtMethod.networks);
}

// Создание депозита USDT
const deposit = await client.createDeposit({
    paymentType: 'usdt',
    amount: 100,
    network: 'TRON'
});
```

**Обработка ПРОМОКОД:**
```javascript
const methods = await client.getPaymentMethods();
const promoMethod = methods.data.find(m => m.code === 'prm');

if (promoMethod?.no_deposit_required) {
    // Промокод не создаёт депозит - используем отдельный endpoint
    const result = await client.activatePromocode({ code: 'MYCODE' });
}
```

**Каталог предзаказов (JavaScript):**
```javascript
// 1. Получение городов с предзаказами
const cities = await client.getPreorderCities();
// cities.data = [{id: 1, title: "Москва", preorder_published: true, ...}, ...]

// 2. Получение товаров для предзаказа в городе
const products = await client.getPreorderProducts(cityId);
// products.city = {id: 1, title: "Москва"}
// products.data = [{
//   id: 5, title: "Товар", amount: 1500, is_preorder: true,
//   locations: [{id: 10, title: "Район", sublocations: [...]}]
// }, ...]

// 3. Получение районов для конкретного товара
const locations = await client.getPreorderLocations(cityId, productId);
// locations.product = {id: 5, title: "Товар", amount: 1500}
// locations.data = [{id: 10, title: "Район", link_to_bot: "?start=preorder_5_10", ...}]

// 4. Создание предзаказа
const purchase = await client.createPurchase({
    product_id: productId,
    location_id: locationId,
});
```

**Каталог предзаказов (Python):**
```python
# 1. Получение городов
cities = client.get_preorder_cities()

# 2. Получение товаров в городе
products = client.get_preorder_products(city_id=1)

# 3. Получение районов
locations = client.get_preorder_locations(city_id=1, product_id=5)

# 4. Создание предзаказа
purchase = client.create_purchase(product_id=5, location_id=10)
```

---

## [1.8.1] - 2026-01-19

### Added
- **Фильтрация покупок по статусу** — новый параметр `status` в методе `getPurchases()`.
  - `'1'` — создан
  - `'2'` — выполнен
  - `'3'` — отменён
  - `'4'` — спор

- **Фильтрация покупок по типу** — новый параметр `is_preorder` в методе `getPurchases()`.
  - `true` — только предзаказы
  - `false` — только обычные покупки
  - Фильтры можно комбинировать: `status=2&is_preorder=true`

### Changed
- **Ограничение отправки сообщений** — метод `sendPurchaseMessage()` теперь запрещает отправку сообщений для выполненных покупок, которые НЕ являются предзаказами.
  - Статус "спор" — сообщения разрешены всегда
  - Статус "выполнена" + предзаказ — сообщения разрешены
  - Статус "выполнена" + обычная покупка — **сообщения запрещены** (ошибка `MESSAGES_NOT_ALLOWED`)

### Usage Examples

**Python:**
```python
# Все покупки
purchases = client.get_purchases()

# Только выполненные
completed = client.get_purchases(status='2')

# Только предзаказы
preorders = client.get_purchases(is_preorder=True)

# Выполненные предзаказы
completed_preorders = client.get_purchases(status='2', is_preorder=True)
```

**JavaScript:**
```javascript
// Все покупки
const purchases = await client.getPurchases();

// Только в споре
const disputes = await client.getPurchases({ status: '4' });

// Только предзаказы
const preorders = await client.getPurchases({ isPreorder: true });

// Выполненные предзаказы
const completedPreorders = await client.getPurchases({ status: '2', isPreorder: true });
```

**PHP:**
```php
// Все покупки
$purchases = $client->getPurchases();

// Только предзаказы
$preorders = $client->getPurchases(null, null, true);

// Выполненные предзаказы
$completedPreorders = $client->getPurchases(null, '2', true);
```

**Go:**
```go
// Все покупки
purchases, _ := client.GetPurchases(PurchasesFilter{})

// Только предзаказы
preorders, _ := client.GetPurchases(PurchasesFilter{IsPreorder: "true"})

// Выполненные предзаказы
completedPreorders, _ := client.GetPurchases(PurchasesFilter{Status: "2", IsPreorder: "true"})
```

### Error Codes
| Код | Описание |
|-----|----------|
| `MESSAGES_NOT_ALLOWED` | Сообщения запрещены для выполненных не-предзаказов |

---

## [1.8.0] - 2026-01-18

### Added
- **Новые поля для реализации фронтенда покупок** — добавлены поля для корректного отображения UI и управления действиями пользователя.

### Новые поля в списке покупок (`getPurchases`)

| Поле | Тип | Назначение |
|------|-----|------------|
| `status_display` | string | Человекочитаемый статус ("Создана", "Выполнена", "Отмена", "Открыт спор") — **для отображения в UI** |
| `is_preorder` | boolean | Флаг предзаказа — **влияет на возможность отправки сообщений** |
| `doned_at` | datetime\|null | Время выполнения — **для отображения в списке** |

### Новые поля в деталях покупки (`getPurchase`)

| Поле | Тип | Назначение |
|------|-----|------------|
| `status_display` | string | Человекочитаемый статус — **для отображения в UI** |
| `is_preorder` | boolean | Флаг предзаказа |
| `can_send_message` | boolean | Можно ли отправить сообщение — **для показа/скрытия формы сообщений** |
| `dispute_expires_at` | datetime\|null | Когда истечёт возможность открыть спор — **для таймера обратного отсчёта** |
| `review_expires_at` | datetime\|null | Когда истечёт возможность оставить отзыв — **для таймера обратного отсчёта** |
| `next_message_available_at` | datetime\|null | Когда можно отправить следующее сообщение — **для блокировки формы с таймером** |

### Логика полей

**`can_send_message`:**
- `true` если статус = "Открыт спор" (всегда можно писать в споре)
- `true` если статус = "Выполнена" И это предзаказ (`is_preorder=true`)
- `false` во всех остальных случаях

**`dispute_expires_at`:**
- Возвращает datetime если можно открыть спор (для показа "Осталось X часов")
- Возвращает `null` если: споры отключены, уже был спор, время истекло, покупка не выполнена

**`review_expires_at`:**
- Возвращает datetime если можно оставить отзыв (для показа "Осталось X часов")
- Возвращает `null` если: отзывы отключены, отзыв уже есть, время истекло

**`next_message_available_at`:**
- Возвращает datetime если действует rate limit (для показа "Подождите X минут")
- Возвращает `null` если можно отправлять сообщение сейчас

### Response Format

**Список покупок:**
```json
{
  "data": [
    {
      "pk": 123,
      "product_title": "Товар",
      "location_title": "Район > Подрайон",
      "amount": 1500,
      "status": "2",
      "status_display": "Выполнена",
      "has_review": false,
      "is_dispute_open": false,
      "is_preorder": false,
      "trouble_at": null,
      "doned_at": "2026-01-18T10:00:00Z",
      "created": "2026-01-18T09:55:00Z"
    }
  ]
}
```

**Детали покупки:**
```json
{
  "data": {
    "pk": 123,
    "status": "2",
    "status_display": "Выполнена",
    "is_preorder": false,
    "can_open_dispute": true,
    "dispute_expires_at": "2026-01-19T10:00:00Z",
    "can_leave_review": true,
    "review_expires_at": "2026-01-19T10:00:00Z",
    "can_send_message": false,
    "next_message_available_at": null,
    "is_dispute_open": false,
    "trouble_at": null,
    "messages_history": []
  }
}
```

### Рекомендации для фронтенда

```javascript
// Показ кнопки "Открыть спор"
if (purchase.can_open_dispute) {
    showDisputeButton();
    if (purchase.dispute_expires_at) {
        showCountdown(purchase.dispute_expires_at, 'Осталось для спора');
    }
}

// Показ кнопки "Оставить отзыв"
if (purchase.can_leave_review) {
    showReviewButton();
    if (purchase.review_expires_at) {
        showCountdown(purchase.review_expires_at, 'Осталось для отзыва');
    }
}

// Показ формы сообщений
if (purchase.can_send_message) {
    showMessageForm();
    if (purchase.next_message_available_at) {
        disableForm();
        showCountdown(purchase.next_message_available_at, 'Подождите');
    }
}

// Показ кнопки "Закрыть спор"
if (purchase.is_dispute_open) {
    showCloseDisputeButton();
}
```

---

## [1.7.1] - 2026-01-18

### Added
- **Новое поле `no_discount` в товарах** — булево поле, указывающее что на товар не распространяются скидки.
  - Затрагивает endpoints: `/merchant/cities/{city_id}/products/`, `/merchant/cities/{city_id}/locations/`, `/merchant/preorder/cities/`

---

## [1.7.0] - 2026-01-18

### Added
- **Новое поле `available_address_types` в товарах** — для каждого товара теперь возвращается список доступных типов адресов с информацией о наценках.
  - Затрагивает endpoints: `/merchant/cities/{city_id}/products/`, `/merchant/cities/{city_id}/locations/`
  - Доступные типы определяются по реальным точкам (MerchantPoint) с `is_available=True`, `is_selled=False`, `is_selled_manual=False`
  - Наценки берутся из MerchantProductKindAddressTypeExtra

### Response Format

**Товар:**
```json
{
  "pk": 123,
  "title": "Товар",
  "available_address_types": [
    {
      "code": "",
      "name": "Не указан",
      "charge": 0
    },
    {
      "code": "magnit",
      "name": "магнит",
      "charge": 0
    },
    {
      "code": "tainik",
      "name": "тайник",
      "charge": 50
    }
  ],
  "amount": 1000,
  ...
}
```

### Notes
- Типы адресов сортируются: пустой код первым, остальные по алфавиту
- `code: ""` означает "Не указан" (точки без указания типа адреса)
- Названия типов берутся из настроек мерчанта (кастомные названия) или используются дефолтные
- Если для типа нет наценки, возвращается `charge: 0`
- Товары без доступных типов адресов возвращают пустой массив `[]`

---

## [1.6.0] - 2026-01-18

### Added
- **Новое поле `parent` в ответе районов** — для подрайонов теперь возвращается объект родительского района с полями `pk` и `title`.
  - Затрагивает endpoints: `/merchant/cities/{city_id}/products/`, `/merchant/cities/{city_id}/locations/`
  - Также добавлено в API предзаказов

### Response Format

**Для подрайона:**
```json
{
  "pk": 101,
  "title": "Арбат",
  "parent": {
    "pk": 100,
    "title": "ЦАО"
  },
  "parent_id": 100,
  "sublocations": []
}
```

**Для района верхнего уровня:**
```json
{
  "pk": 100,
  "title": "ЦАО",
  "parent": null,
  "parent_id": null,
  "sublocations": [
    {"id": 101, "title": "Арбат"}
  ]
}
```

### Notes
- Поле `parent_id` сохранено для обратной совместимости
- Формат ответа (массив) не изменился

---

## [1.5.3] - 2026-01-17

### Added
- **Новые поля в ответе покупки** (`getPurchase`):
  - `reviews_available` — включены ли отзывы в магазине
  - `disputes_available` — включены ли споры в магазине
  - `can_leave_review` — можно ли оставить отзыв (с учётом всех ограничений)
  - `can_open_dispute` — можно ли открыть спор (с учётом всех ограничений, включая `disputes_available`)
  - `is_returned`, `returned_at` — информация о возврате
  - `is_replaced`, `replaced_at` — информация о замене
  - В объекте `review` добавлены: `status_display`, `is_pending`, `is_rejected`

- **Новые поля в ответе депозита** (`getDeposit`):
  - `can_open_dispute` — можно ли открыть спор (с учётом времени из настроек мерчанта)

### Changed
- **createReview()** — добавлена проверка `review_available`. Если отзывы отключены в магазине, возвращается ошибка `REVIEWS_DISABLED`.
- **openDispute()** — добавлена проверка `purchase_can_disput`. Если споры отключены в магазине, возвращается ошибка `DISPUTES_DISABLED`.
- **can_open_dispute для депозитов** — время на открытие спора теперь берётся из настроек мерчанта (`disput_delay`), а не хардкод 3 часа.

### Response Format

**Покупка:**
```json
{
  "pk": 123,
  "reviews_available": true,
  "disputes_available": true,
  "can_leave_review": true,
  "can_open_dispute": true,
  "has_review": true,
  "review": {
    "pk": 456,
    "rate": 5,
    "text": "Отличный товар!",
    "status": "published",
    "status_display": "Опубликован",
    "is_published": true,
    "is_pending": false,
    "is_rejected": false,
    "answer": "Спасибо!",
    "created": "2026-01-17T12:00:00Z"
  },
  "is_returned": false,
  "returned_at": null,
  "is_replaced": false,
  "replaced_at": null
}
```

**Депозит:**
```json
{
  "pk": 456,
  "can_open_dispute": true,
  "status": "canceled_at"
}
```

---

## [1.5.2] - 2026-01-17

### Added
- **closeDispute(purchaseId)** — новый метод для закрытия спора по покупке (клиент подтверждает решение).
- **getPurchaseMessages(purchaseId)** — получение списка сообщений по покупке.
- **sendPurchaseMessage(purchaseId, {text, file})** — отправка сообщения по покупке (в споре).
- **createReview(purchaseId, rate, text)** — создание отзыва по покупке с теми же ограничениями что и в боте:
  - Покупка должна быть завершена (статус "Выполнена")
  - Не позднее 1 дня после завершения покупки
  - Один отзыв на покупку
  - Текст минимум 5 символов
  - Текст не должен повторяться
  - Оценка от 1 до 5

### Usage Examples

**Python:**
```python
# Закрыть спор
client.close_dispute(123)

# Получить сообщения
messages = client.get_purchase_messages(123)
for msg in messages['data']:
    print(f"{msg['created']}: {msg['text']}")

# Отправить сообщение
client.send_purchase_message(123, text='Фото проблемы')

# Отправить файл
with open('photo.jpg', 'rb') as f:
    client.send_purchase_message(123, file=f, file_name='photo.jpg')

# Оставить отзыв
review = client.create_review(123, 5, 'Отличный товар, рекомендую!')
print(f"Отзыв #{review['data']['pk']} создан")
```

**JavaScript:**
```javascript
// Закрыть спор
await client.closeDispute(123);

// Получить сообщения
const messages = await client.getPurchaseMessages(123);

// Отправить сообщение
await client.sendPurchaseMessage(123, { text: 'Проблема с товаром' });

// Отправить файл
await client.sendPurchaseMessage(123, { file, fileName: 'photo.jpg' });

// Оставить отзыв
const review = await client.createReview(123, 5, 'Отличный товар!');
console.log(`Отзыв #${review.data.pk} создан`);
```

**PHP:**
```php
// Закрыть спор
$client->closeDispute(123);

// Получить сообщения
$messages = $client->getPurchaseMessages(123);

// Отправить сообщение
$client->sendPurchaseMessage(123, 'Проблема с товаром');

// Отправить файл
$client->sendPurchaseMessage(123, null, '/path/to/photo.jpg');

// Оставить отзыв
$review = $client->createReview(123, 5, 'Отличный товар!');
echo "Отзыв #{$review['data']['pk']} создан";
```

**Go:**
```go
// Закрыть спор
client.CloseDispute(123)

// Получить сообщения
messages, _ := client.GetPurchaseMessages(123)

// Отправить сообщение
client.SendPurchaseMessage(123, SendPurchaseMessageParams{
    Text: "Проблема с товаром",
})

// Отправить файл
file, _ := os.Open("/path/to/photo.jpg")
client.SendPurchaseMessage(123, SendPurchaseMessageParams{
    File:     file,
    FileName: "photo.jpg",
})

// Оставить отзыв
review, _ := client.CreateReview(123, 5, "Отличный товар!")
```

---

## [1.5.1] - 2026-01-17

### Added
- **regenerateAuthCode()** — новый метод для перегенерации кода авторизации. Ограничение: не чаще 1 раза в час. Возвращает обновлённый профиль клиента.

### Changed
- **openDispute()** — метод больше не требует параметр `text` (причина спора). Вызов теперь: `openDispute(purchaseId)` вместо `openDispute(purchaseId, text)`.
- **location_title** — в ответах покупок и отзывов теперь показывается иерархия локации в формате "Район > Подрайон" если есть родительский район.

### Fixed
- **PersonalDiscountSerializer** — исправлены несуществующие поля `expires_at` и `is_active`. Добавлены `used_at`, `discount_kind`, `discount_str`.
- **LotteryParticipationSerializer** — исправлен расчёт суммы выигрыша (`prize_amount`).
- **PurchaseCreateView** — исправлены поля фильтрации товаров и локаций.

---

## [1.5.0] - 2026-01-16

### Added
- **Расширенный профиль клиента** — метод `getProfile()` теперь возвращает 37 полей вместо 11:
  - Персональные данные: `username`, `first_name`, `last_name`, `avatar` (URL)
  - Настройки: `lang` (теперь возвращает код языка, например "ru", вместо FK), `discount`
  - Флаги банов: `is_banned_for_promos`, `is_banned_for_lucky`, `is_banned_for_casino`, `is_banned_for_ruletka`, `is_banned_for_privatebot`, `is_banned_for_referal`
  - Web-авторизация: `web_auth_code`, `web_auth_code_created_at`, `web_last_login_at`
  - Статистика: `referals_count`, `deposit_count`, `purchase_count`, `doned_purchase_count`, `total_spent`, `trouble_purchase_count`, `purchase_promocoded_count`, `returned_purchase_count`, `opened_disput_count`, `last_returned_at`, `changed_count`, `last_changed_at`

### Changed
- **TypeScript** — добавлен интерфейс `ClientProfile` с типизацией всех полей
- **JSDoc** — метод `getProfile()` теперь возвращает типизированный объект

### Response Format
```json
{
  "result": "success",
  "data": {
    "pk": 123,
    "balance": 1500.00,
    "currency": "RUB",
    "telegram_linked": true,
    "uid": "123456789",
    "username": "user123",
    "first_name": "Иван",
    "last_name": "Петров",
    "avatar": "https://cdn.example.com/avatars/123.jpg",
    "lang": "ru",
    "discount": 5.0,
    "is_banned": false,
    "is_banned_for_reviews": false,
    "is_banned_for_promos": false,
    "is_banned_for_disputs": false,
    "web_auth_code": "tiger-4829-ocean",
    "referals_count": 3,
    "deposit_count": 15,
    "purchase_count": 42,
    "doned_purchase_count": 40,
    "total_spent": 25000.00,
    "created": "2025-06-15T10:30:00Z"
  }
}
```

---

## [1.4.0] - 2026-01-16

### Added
- **Константы статусов** - добавлены классы/константы статусов для удобной работы:
  - `DepositStatus` — статусы заявок на пополнение (created, creds_at, waiting_at, payed_at, done_at, trouble_at, expired_at, canceled_at)
  - `PurchaseStatus` — статусы покупок (1=created, 2=done, 3=canceled, 4=trouble)
- **Сообщения по депозитам** - новые методы для работы с сообщениями в заявках на пополнение:
  - `getDepositMessages(depositId)` — получение списка сообщений
  - `sendDepositMessage(depositId, text, file)` — отправка текста, фото или PDF
- **Открытие спора по депозиту** - новый метод `openDepositDispute(depositId)`
  - Доступно только для отменённых/просроченных заявок
  - В течение 3 часов после отмены
  - При наличии выданных реквизитов
- **Новые поля дат в ответе депозита**: `creds_at`, `waiting_at`, `trouble_at`, `expired_at`

### Response Format
Формат сообщений соответствует формату бота:
```json
{
  "data": [
    {"message": "Текст сообщения 16.01.2026 12:00", "is_user": true},
    {"message": "Ответ оператора 16.01.2026 12:05", "is_user": false}
  ]
}
```

### Usage Examples

**Python:**
```python
# Получить сообщения по заявке
result = client.get_deposit_messages(123)
for msg in result['data']:
    sender = 'Клиент' if msg['is_user'] else 'Оператор'
    print(f"{sender}: {msg['message']}")

# Отправить текстовое сообщение
client.send_deposit_message(123, text='Оплатил, жду подтверждения')

# Отправить фото чека
with open('receipt.jpg', 'rb') as f:
    client.send_deposit_message(123, file=f, file_name='receipt.jpg')

# Открыть спор
client.open_deposit_dispute(123)
```

**JavaScript:**
```javascript
// Получить сообщения
const result = await client.getDepositMessages(123);
result.data.forEach(msg => {
    const sender = msg.is_user ? 'Клиент' : 'Оператор';
    console.log(`${sender}: ${msg.message}`);
});

// Отправить текст
await client.sendDepositMessage(123, { text: 'Оплатил' });

// Отправить файл (в браузере)
const file = document.querySelector('input[type="file"]').files[0];
await client.sendDepositMessage(123, { file, fileName: file.name });

// Открыть спор
await client.openDepositDispute(123);
```

**PHP:**
```php
// Получить сообщения
$result = $client->getDepositMessages(123);
foreach ($result['data'] as $msg) {
    $sender = $msg['is_user'] ? 'Клиент' : 'Оператор';
    echo "{$sender}: {$msg['message']}\n";
}

// Отправить текст
$client->sendDepositMessage(123, 'Оплатил');

// Отправить файл
$client->sendDepositMessage(123, null, '/path/to/receipt.jpg');

// Открыть спор
$client->openDepositDispute(123);
```

**Go:**
```go
// Получить сообщения
result, _ := client.GetDepositMessages(123)
for _, msg := range result["data"].([]interface{}) {
    m := msg.(map[string]interface{})
    sender := "Оператор"
    if m["is_user"].(bool) {
        sender = "Клиент"
    }
    fmt.Printf("%s: %s\n", sender, m["message"])
}

// Отправить текст
client.SendDepositMessage(123, SendDepositMessageParams{
    Text: "Оплатил, жду подтверждения",
})

// Отправить файл
file, _ := os.Open("/path/to/receipt.jpg")
client.SendDepositMessage(123, SendDepositMessageParams{
    File:     file,
    FileName: "receipt.jpg",
})

// Открыть спор
client.OpenDepositDispute(123)
```

---

## [1.3.0] - 2026-01-16

### Added
- **Фильтрация пополнений по статусу** - новый параметр `status` в `getDeposits()`
  - `active` — активные заявки (ожидают оплаты, назначения реквизитов)
  - `completed` — выполненные заявки
  - `canceled` — отменённые и просроченные заявки
  - `dispute` — заявки в споре
- **Новый метод `getActiveDeposit()`** - получение активной заявки на пополнение (у клиента может быть только одна)

### Usage Examples

**Python:**
```python
# Получить все пополнения
deposits = client.get_deposits()

# Получить только активные заявки
active = client.get_deposits(status='active')

# Получить выполненные заявки с пагинацией
completed = client.get_deposits(page=2, status='completed')

# Удобный метод для получения активной заявки
active_deposit = client.get_active_deposit()
if active_deposit:
    print(f"Активная заявка #{active_deposit['pk']}")
```

**JavaScript:**
```javascript
// Получить только активные заявки
const active = await client.getDeposits({ status: 'active' });

// Удобный метод
const activeDeposit = await client.getActiveDeposit();
```

**PHP:**
```php
// Получить активные заявки
$active = $client->getDeposits(null, 'active');

// Удобный метод
$activeDeposit = $client->getActiveDeposit();
```

**Go:**
```go
// Получить активные заявки
active, _ := client.GetDeposits(DepositsFilter{Status: "active"})

// Удобный метод
activeDeposit, _ := client.GetActiveDeposit()
```

---

## [1.2.0] - 2026-01-14

### Added
- **Web Client API SDK** - Новый клиент `WebClientApiClient` для авторизации покупателей на сайте магазина
- Двухуровневая авторизация: MerchantApiKey + клиентская сессия
- 25 новых endpoints для работы с личным кабинетом покупателя:
  - Регистрация/вход через captcha
  - Профиль и привязка Telegram
  - Пополнение баланса
  - Покупки и споры
  - Отзывы, поддержка, промокоды
  - Подписки, розыгрыши, персональные скидки

### Changed
- Авторизация Web Client API изменена с X-Merchant-Domain на MerchantApiKey
- Клиентская сессия теперь передаётся в заголовке X-Client-Session

### Usage (Python)
```python
from merchant_api import WebClientApiClient

client = WebClientApiClient(
    base_url='https://example.onion',
    api_key='your_merchant_api_key'
)

# Регистрация
captcha = client.get_captcha()
result = client.register(captcha['captcha_id'], 'answer')
print(f"Ваш код: {result['auth_code']}")  # Сохраните!

# Защищённые методы (после login/register)
profile = client.get_profile()
```

---

## [1.1.0] - 2026-01-11

### Added
- Новый раздел "Работа с подрайонами" во всех SDK (Python, JavaScript, PHP, Go)
- Примеры построения иерархии город → район → подрайон
- Примеры фильтрации товаров по конкретному подрайону
- React компонент `LocationSelector` для двухуровневого выбора район/подрайон (JavaScript SDK)
- Laravel контроллер для API выбора подрайонов с optgroup (PHP SDK)
- Gin endpoint для получения структурированных подрайонов (Go SDK)
- Примеры создания адресов с указанием подрайона

### Documentation
- Обновлена нумерация разделов во всех README файлах
- Добавлены примеры JSON ответов для работы с подрайонами

---

## [1.0.0] - 2026-01-10

### Added
- Initial release of Merchant API SDK
- Support for all 14 API endpoints
- TOR proxy support (enabled by default, recommended)
- Webhook signature verification (HMAC-SHA256)
- Available for 4 languages: Python, JavaScript, PHP, Go
- Automatic TOR installation script

### Backwards Compatibility
- This is the initial release, no backwards compatibility concerns.

---

## Migration Guide

### From version X.X.X to Y.Y.Y
_(Migration instructions will be added here when new versions are released)_

---

## API Compatibility

| SDK Version | API Version | Status |
|-------------|-------------|--------|
| 1.11.1 | v1 | Current |
| 1.11.0 | v1 | Supported |
| 1.10.3 | v1 | Supported |
| 1.10.2 | v1 | Supported |
| 1.10.1 | v1 | Supported |
| 1.9.1 | v1 | Supported |
| 1.9.0 | v1 | Supported |
| 1.8.1 | v1 | Supported |
| 1.8.0 | v1 | Supported |
| 1.7.x | v1 | Supported |
| 1.6.0 | v1 | Supported |
| 1.5.3 | v1 | Supported |
| 1.5.2 | v1 | Supported |
| 1.5.1 | v1 | Supported |
| 1.5.0 | v1 | Supported |
| 1.4.0 | v1 | Supported |
| 1.3.0 | v1 | Supported |
| 1.2.0 | v1 | Supported |
| 1.1.0 | v1 | Supported |
| 1.0.0 | v1 | Supported |
