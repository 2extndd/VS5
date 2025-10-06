# 🔍 Vinted Scanner Bot - Полная Документация Систем

## 📋 Обзор

**Vinted Scanner Bot** - это высокотехнологичная система для автоматизированного поиска и мониторинга товаров на платформе Vinted. Бот использует продвинутые методы обхода анти-бот систем и обеспечивает надежную работу 24/7.

---

## 🏗️ Архитектура Системы

### Основные Компоненты

1. **Core Engine** (`core.py`) - Логика сканирования и обработки
2. **Vinted API Wrapper** (`pyVintedVN/`) - Интерфейс к Vinted API
3. **Token Pool System** (`token_pool.py`) - Управление токенами аутентификации
4. **Proxy System** (`proxies.py`) - Ротация прокси серверов
5. **Railway Auto-Redeploy** (`railway_redeploy.py`) - Автоматический редеплой
6. **Web UI** (`web_ui_plugin/`) - Панель управления
7. **Telegram Integration** (`telegram_bot_plugin/`) - Уведомления в Telegram
8. **Database** (`db.py`) - Хранение данных и конфигурации

---

## 🔍 Система Поиска Товаров

### Как Бот Ищет Вещи

#### 1️⃣ Конфигурация Поисковых Запросов

```sql
-- Структура таблицы queries
CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT,           -- URL поискового запроса Vinted
    last_item NUMERIC,    -- ID последнего найденного товара
    query_name TEXT,      -- Название для отображения
    thread_id INTEGER     -- ID воркера (для распределения нагрузки)
);
```

**Пример запроса:**
```
https://www.vinted.de/catalog?search_text=&catalog_ids=257&brand_ids=6397426&size_ids=&material_ids=&status_ids=&country_ids=&city_ids=&is_for_swap=&currency=EUR&price_to=40&price_from=&page=1&per_page=2&order=newest_first&time=
```

#### 2️⃣ Параллельная Обработка

- **72 независимых воркера** (по одному на каждый query)
- **ThreadPoolExecutor** для параллельного выполнения
- **Каждый воркер** сканирует свой query каждые N секунд
- **⚡ МГНОВЕННЫЙ СТАРТ** - все воркеры стартуют одновременно (нет staggered delay!)

```python
# core.py - запуск воркеров (БЕЗ ЗАДЕРЖЕК!)
executor = ThreadPoolExecutor(max_workers=len(all_queries))

# Все воркеры стартуют МГНОВЕННО с start_delay=0
for idx, query in enumerate(all_queries):
    executor.submit(continuous_query_worker, query, queue, start_delay=0)
```

**🔥 Почему нет staggered start:**
- Токены уже **pre-warmed** (созданы заранее)
- Воркеры не создают токены при старте (берут готовые из pool)
- Все 72 воркера начинают сканировать **одновременно**

#### 3️⃣ Цикл Сканирования Воркера

```python
def continuous_query_worker(query, queue, start_delay=0):
    while True:
        # 1. Читает параметры из БД динамически
        refresh_delay = db.get_parameter("query_refresh_delay") or 15
        items_per_query = db.get_parameter("items_per_query") or 20

        # 2. Получает уникальный токен из пула
        token_session = token_pool.get_session_for_worker(query_id)

        # 3. Делает запрос к Vinted API
        search_result = vinted.items.search(query_url, nbr_items=items_per_query)

        # 4. Обрабатывает результат (успех/ошибка)
        # 5. Спит refresh_delay секунд
        time.sleep(refresh_delay)
```

#### 4️⃣ Обработка Результатов

- **Успешные товары** → добавляются в базу данных
- **Дубликаты** → пропускаются
- **Новые товары** → отправляются в Telegram и Web UI

---

## 🤖 Суперчат в Telegram

### Структура Суперчата

Бот использует **Telegram Super Group** с топиками для организации уведомлений:

```
/superchat
├── 📱 Tech & Phones (topic_id: 1)
├── 👕 Fashion (topic_id: 2)
├── 🏠 Home & Garden (topic_id: 3)
├── 🎮 Gaming (topic_id: 4)
└── 💼 Business (topic_id: 5)
```

### Логика Распределения

1. **Определение категории** товара по ключевым словам
2. **Маппинг категории** на topic_id в базе данных
3. **Отправка сообщения** в соответствующий топик

```python
# Определение категории по ключевым словам
categories = {
    "phone": 1, "iphone": 1, "samsung": 1, "tech": 1,
    "fashion": 2, "clothing": 2, "shoes": 2,
    "home": 3, "furniture": 3, "garden": 3,
    "gaming": 4, "ps5": 4, "xbox": 4,
    "business": 5, "laptop": 5, "office": 5
}
```

### Формат Сообщений

```
💶40.0 EUR (+3 min) ⛓️ 43 Dior
[Фото товара]
[Ссылка на товар]
```

- **Цена** с валютой
- **Задержка** обнаружения (+X min)
- **Количество фото** (⛓️ X)
- **Бренд** товара

---

## 🛡️ Системы Защиты от Бана

### 1️⃣ Token Pool System

#### 🔥 PRE-WARMING: Токены Создаются ДО Старта Воркеров

```python
class TokenPool:
    def __init__(self, target_size=72, max_size=100, prewarm=True):
        self.target_size = target_size  # 72 токена для 72 воркеров
        self.sessions = []  # Пул активных сессий
        
        # 🔥 PRE-WARMING: создаем ВСЕ токены сразу при инициализации
        if prewarm:
            self._prewarm_pool()
    
    def _prewarm_pool(self):
        """
        Создает ВСЕ 72 токена ЗАРАНЕЕ (до старта воркеров).
        Это позволяет воркерам стартовать МГНОВЕННО!
        """
        for i in range(self.target_size):
            proxy_dict = proxies.get_random_proxy()
            session = self._create_new_session_with_proxy(proxy_dict)
            if session:
                self.sessions.append(session)
            
            # Небольшая задержка между созданием токенов
            # 0.8 сек × 72 = ~60 секунд на весь пул
            time.sleep(0.8)
        
        # После pre-warming все токены готовы!
        # Воркеры могут стартовать МГНОВЕННО

    def get_session_for_worker(self, worker_id):
        # Воркер просто БЕРЕТ готовый токен (не создает!)
        session_idx = worker_id % len(self.sessions)
        return self.sessions[session_idx]
```

**Преимущества Pre-warming:**
- ✅ Все токены создаются **ДО** старта воркеров (за ~60 сек)
- ✅ Воркеры стартуют **МГНОВЕННО** (нет задержки на создание токенов)
- ✅ Первый скан происходит **СРАЗУ** для всех 72 воркеров
- ✅ Задержка между находками = **ТОЛЬКО Query Refresh Delay** (60 сек)
- ✅ Нет больше задержек в 3-5 минут между воркерами!

#### 12 Разных User-Agent'ов

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # ... и другие варианты
]
```

#### Автоматическая Замена Токенов

- **5+ ошибок** → токен помечается невалидным
- **Следующий запрос** → токен удаляется и создается новый
- **Постепенное создание** → не все токены сразу (анти rate limit)

### 2️⃣ Proxy Rotation System

#### Динамическая Ротация Прокси

```python
# Каждый запрос меняет прокси
if self.request_count % self.proxy_rotation_interval == 0:
    self.set_random_proxy()

# По умолчанию: каждый запрос = новый прокси
proxy_rotation_interval = 1
```

#### Пул из 196 Рабочих Прокси

- **Источник:** webshare.io (100 прокси)
- **Проверка:** каждые 30 минут на vinted.de
- **Валидация:** 2xx/3xx статус коды, timeout 10 сек

#### Исключение Проблемных Прокси

```python
def rotate_proxy(self):
    current_proxy = self.session.proxies.get('http', '')
    # Получаем новый прокси, ИСКЛЮЧАЯ текущий "плохой"
    new_proxy = proxies.get_fresh_proxy(exclude_proxy=current_proxy_str)
```

### 3️⃣ Rate Limiting & Request Delays

#### Query Refresh Delay

- **Настраиваемый** через Web UI (по умолчанию 60 сек)
- **Читается динамически** из БД каждую итерацию
- **Применяется к каждому воркеру** независимо

#### ❌ Staggered Worker Start - УДАЛЕН!

**СТАРАЯ система (до 06.10.2025):**
```python
# Воркеры стартовали с задержками (создавало 3-5 мин разницу в находках!)
start_delay = (idx * 60.0) / num_queries  # ❌ БОЛЬШЕ НЕ ИСПОЛЬЗУЕТСЯ
```

**НОВАЯ система (с 06.10.2025):**
```python
# ВСЕ воркеры стартуют МГНОВЕННО
start_delay = 0  # ✅ Нет задержек!

# Защита от бана теперь через:
# 1. Pre-warming токенов (создаются ДО старта воркеров)
# 2. Token Pool с уникальными токенами
# 3. Proxy rotation для каждого запроса
```

### 4️⃣ Session Management

#### Bearer Авторизация

```python
# Получение токена с главной страницы
response = session.get("https://www.vinted.de/")
access_token = session.cookies['access_token_web']

# Добавление в заголовки
session.headers["Authorization"] = f"Bearer {access_token}"
```

#### Автообновление Токенов

- **При 401/403 ошибках** → обновление токена
- **До 5 попыток** с новым токеном
- **Fallback** на создание новой сессии

### 5️⃣ Request Headers Emulation

#### Реалистичные Заголовки

```python
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"
}
```

---

## 👥 Workers Status (Last 3 Cycles)

### Реалтайм Мониторинг Воркеров

#### Структура Данных

```python
_worker_stats = {
    worker_id: {
        'last_success': datetime,     # Последний успешный скан
        'last_error': datetime,       # Последняя ошибка
        'total_scans': int,          # Общее количество сканов
        'total_items': int,          # Найденные товары
        'total_errors': int,         # Количество ошибок
        'recent_scans': [            # Последние 3 цикла
            {'time': datetime, 'status': 'success/error', 'items': int}
        ]
    }
}
```

#### Логика Статуса

```javascript
// Определяем статус по последним 3 циклам
const hasRecentErrors = recentScans.some(scan => scan.status === 'error');

if (hasRecentErrors) {
    // Показываем в секции ошибок
    errorWorkers.push(workerData);
} else {
    // Показываем в активных
    activeWorkers.push(workerData);
}
```

#### Визуализация

- **Бейджи:** `✅N` (успешный), `❌N` (ошибки), `📭N` (без вещей)
- **Статистика:** Total | Working OK | Recent Errors | Idle
- **Детали ошибок:** Свернутая секция с историей

---

## 🚨 Railway Auto-Redeploy System

### Автоматический Рестарт при Проблемах

#### Условия Рестарта

1. **Нормальный рестарт:**
   - Прошло ≥ threshold_minutes с первой ошибки
   - Накопилось ≥ max_http_errors ошибок

2. **Критический рестарт:**
   - Накопилось ≥ 100 ошибок (любого типа)

3. **Принудительный рестарт:**
   - Через Web UI кнопка "Force Redeploy"

#### Параметры (Настраиваемые)

```sql
-- В базе данных
redeploy_threshold_minutes = 4  -- Минут с первой ошибки
max_http_errors = 5             -- Мин. ошибок для рестарта
min_redeploy_interval_minutes = 3 -- Мин. интервал между рестартами
```

#### 6-Уровневая Цепочка Рестарта (с 06.10.2025)

```python
def _perform_redeploy(self):
    # 1️⃣ Попытка через Railway GraphQL API
    if self.api_token:
        response = requests.post("https://backboard.railway.com/graphql/v2",
                                json=payload, headers=headers)
        if success: return True
    
    # 2️⃣ Fallback через Railway CLI
    result = subprocess.run(["railway", "redeploy", "-y"])
    if result.returncode == 0: return True
    
    # 3️⃣ Fallback через HTTP REST API
    response = requests.post(
        f"https://backboard.railway.com/projects/{project_id}/services/{service_id}/redeploy",
        headers={"Authorization": f"Bearer {api_token}"}
    )
    if response.status_code in [200, 201, 202]: return True
    
    # 4️⃣ Emergency: попытка через Webhook
    if webhook_url:
        response = requests.post(webhook_url)
        if response.status_code in [200, 201, 202]: return True
    
    # 5️⃣ Emergency Exit (если включен ALLOW_EMERGENCY_EXIT=true)
    if os.getenv('ALLOW_EMERGENCY_EXIT') == 'true':
        # Отправляем SIGTERM самому себе
        os.kill(os.getpid(), signal.SIGTERM)  # Exit code 143 (graceful shutdown)
        # Railway автоматически перезапустит контейнер
        return True
    
    # 6️⃣ Fake Redeploy (последний fallback, БЕЗ краша)
    # Просто сбрасываем счетчики ошибок и продолжаем работу
    self._reset_error_tracking()
    return False
```

#### 🩺 Railway Redeploy - Реальное Состояние

**ЧТО РАБОТАЕТ:**
```python
# os._exit(1) - ЕДИНСТВЕННЫЙ рабочий метод
os._exit(1)  # Railway автоматически перезапускает контейнер

# ALLOW_EMERGENCY_EXIT='true' по умолчанию
```

**ЧТО НЕ РАБОТАЕТ:**
- ❌ Railway GraphQL API → 404 errors
- ❌ Railway CLI → не установлен в контейнере
- ❌ Railway HTTP REST API → 404 Not Found  
- ❌ SIGTERM вместо exit(1) → НЕ перезапускает контейнер
- ⚠️ Webhook → может работать если настроен, но обычно нет

**История изменений:**
1. Была версия cf7b0fb с `os._exit(1)` → РАБОТАЛА ✅
2. Попытка улучшить на SIGTERM → НЕ РАБОТАЛА ❌
3. Вернули `os._exit(1)` → РАБОТАЕТ ✅

**Решение #2: Healthcheck endpoint**
```python
# Новый endpoint: /health и /healthcheck
@app.route('/health')
def healthcheck():
    return jsonify({
        "status": "healthy",
        "workers": len(db.get_queries()),
        "service": "vinted-bot"
    }), 200
```

**Решение #3: railway.json конфигурация**
```json
{
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

**Переменные окружения для редеплоя:**
- `ALLOW_EMERGENCY_EXIT` - разрешить emergency exit через os._exit(1) (по умолчанию `true`)
- `RAILWAY_REDEPLOY_WEBHOOK` - URL webhook для редеплоя (опционально, обычно не работает)
- `RAILWAY_TOKEN` - токен Railway API (обычно не работает - 404 errors)

**⚠️ ВАЖНО:** Railway API/CLI методы НЕ РАБОТАЮТ стабильно (404/403 errors).
Единственный рабочий метод - `os._exit(1)` который включен по умолчанию.

---

## 🚨 Обработка Ошибок

### Полный Алгоритм Обработки Ошибок

#### HTTP Ошибки (401, 403, 429)

```python
# Воркер получает ответ от Vinted API
if isinstance(search_result, tuple) and len(search_result) == 2:
    response, status_code = search_result

    # НЕМЕДЛЕННО сообщаем системе редеплоя
    if status_code == 403:
        report_403_error()  # ← В redeploy system
    elif status_code == 401:
        report_401_error()  # ← В redeploy system
    elif status_code == 429:
        report_429_error()  # ← В redeploy system

    # Сообщаем токен пулу об ошибке
    token_pool.report_error(token_session)

    # Обновляем статистику воркера
    update_worker_stats(query_id, 'error')
```

#### Неожиданные Ошибки

```python
except Exception as e:
    # Любая другая ошибка (network, parsing, etc.)

    # НЕМЕДЛЕННО сообщаем токен пулу
    token_pool.report_error(token_session)

    # НЕМЕДЛЕННО обновляем статистику
    update_worker_stats(query_id, 'error')

    # НЕМЕДЛЕННО сообщаем redeploy system как 403
    report_403_error()

    # Проверяем токен
    if not token_session.is_valid:
        # Получаем новый токен
        token_session = token_pool.get_session_for_worker(query_id)
```

#### Задержка Между Циклами

```python
# Независимо от успеха/ошибки
time.sleep(refresh_delay)  # ← ЖДЕТ СЛЕДУЮЩЕГО ЦИКЛА

# Цикл повторяется...
```

---

## 🌐 Proxy System

### Управление Пулом Прокси

#### Фетчинг Прокси

```python
def fetch_proxies_from_link(url: str) -> List[str]:
    response = requests.get(url, timeout=10)
    return [line.strip() for line in response.text.splitlines() if line.strip()]
```

#### Проверка Прокси

```python
def check_proxies_parallel(proxies_list: List[str]) -> List[str]:
    # Параллельная проверка 10 потоками
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_proxy, proxy) for proxy in proxies_list]
        results = [future.result() for future in as_completed(futures)]

    # Возвращает только рабочие прокси
    return [proxy for proxy, is_valid in results if is_valid]
```

#### Валидация Прокси

```python
def check_proxy(proxy: str) -> tuple[str, bool]:
    try:
        response = requests.get("https://www.vinted.de/",
                              proxies={"http": proxy, "https": proxy},
                              timeout=10, allow_redirects=True)

        # Принимаем 2xx и 3xx статус коды
        return proxy, 200 <= response.status_code < 400
    except:
        return proxy, False
```

#### Ротация Прокси

- **Каждый запрос** → новый прокси (по умолчанию)
- **Исключение проблемных** прокси из ротации
- **Автоматическая проверка** каждые 30 минут

---

## 🖥️ Web UI

### Основные Функции

#### Dashboard (`/`)
- **Статистика бота:** общее количество товаров, запросов, uptime
- **Автообновление:** каждые 10 секунд
- **Responsive дизайн** с карточками

#### Items (`/items`)
- **Список товаров** с пагинацией
- **Фильтры** по категориям и брендам
- **Автообновление:** каждые 10 секунд
- **Card/List view** переключение

#### Configuration (`/config`)
- **Настройки бота:** Query Refresh Delay, Items per Query, etc.
- **Workers Status:** реалтайм мониторинг всех воркеров
- **Railway Status:** мониторинг системы редеплоя
- **Proxy Status:** мониторинг пула прокси

#### Logs (`/logs`)
- **Логи системы** с фильтрацией по уровню
- **Автообновление:** каждые 5 секунд
- **Пагинация** для больших объемов логов

### AJAX Автообновление

#### Конфигурация Интервалов

| Страница | Элемент | Интервал | Функция |
|----------|---------|----------|---------|
| `/` | Dashboard stats | 10 сек | `refreshDashboard()` |
| `/items` | Items list | 10 сек | `refreshItems()` |
| `/logs` | Logs | 5 сек | `fetchLogs()` |
| `/config` | Workers Status | 30 сек | `refreshWorkerStats()` |
| `/config` | Redeploy Status | 30 сек | `refreshRedeployStatus()` |
| `/config` | Proxy Status | 45 сек | `refreshProxyStatus()` |

#### Оптимизация

```javascript
// Не обновлять если вкладка неактивна
if (document.visibilityState !== 'visible') return;

// Экономит трафик и ресурсы
```

---

## 📊 База Данных

### Структура БД

#### Таблицы

1. **queries** - поисковые запросы
2. **items** - найденные товары
3. **allowlist** - разрешенные страны
4. **parameters** - настройки бота

#### Ключевые Параметры

```sql
INSERT INTO parameters (key, value) VALUES
('query_refresh_delay', '60'),           -- Задержка между сканами (сек)
('items_per_query', '20'),               -- Товаров за запрос
('proxy_rotation_interval', '1'),        -- Ротация прокси каждый запрос
('redeploy_threshold_minutes', '4'),     -- Порог редеплоя (мин)
('max_http_errors', '5'),               -- Макс. ошибок для редеплоя
('last_redeploy_time', ''),             -- Время последнего редеплоя
('telegram_enabled', 'False'),          -- Включен ли Telegram
('telegram_token', ''),                 -- Токен бота
('telegram_chat_id', ''),               -- ID суперчата
('bot_start_time', '0');                -- Время запуска бота
```

---

## 🚀 Производительность

### Метрики Производительности

- **72 параллельных воркера** → 72 запроса каждые 60 секунд
- **196 рабочих прокси** → распределение нагрузки
- **Автообновление Web UI** → реалтайм мониторинг
- **Динамическая конфигурация** → изменения применяются мгновенно

### Оптимизации

1. **ThreadPoolExecutor** для параллелизма
2. **Connection pooling** в requests.Session
3. **Оптимизированные запросы** к БД с индексами
4. **Лимитированное логирование** для снижения нагрузки

---

## 🔧 Конфигурация и Развертывание

### Переменные Окружения

```bash
# Railway API (для автоматического редеплоя)
RAILWAY_TOKEN=your_railway_token
RAILWAY_PROJECT_ID=your_project_id
RAILWAY_SERVICE_ID=your_service_id

# Database
DATABASE_URL=your_database_url

# Telegram
TELEGRAM_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# Redeploy Options (опционально)
RAILWAY_REDEPLOY_WEBHOOK=https://your-webhook-url  # Рекомендуется для надежного редеплоя
ALLOW_EMERGENCY_EXIT=true  # Разрешить SIGTERM exit при критических ошибках
```

### Railway Конфигурация

- **Автоматический деплой** из GitHub
- **PostgreSQL база данных** с авто-бэкапами
- **Логи** доступны через Railway dashboard
- **Мониторинг** ресурсов и производительности

#### railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

**⚠️ ВАЖНО:**
- НЕ используйте `startCommand` в railway.json - это перезапишет Procfile
- Команда старта должна быть ТОЛЬКО в `Procfile`
- `railway.json` только для конфигурации restart policy и healthcheck

#### Procfile

```
web: pip install railway && python vinted_notifications.py
```

**Почему `pip install railway`:**
- Railway CLI нужен для метода #2 редеплоя
- Устанавливается при каждом деплое для гарантии доступности

---

## 🎯 Заключение

**Vinted Scanner Bot** представляет собой комплексную систему с множеством уровней защиты, параллельной обработкой и реалтайм мониторингом. Система спроектирована для максимальной надежности и эффективности при минимальном риске обнаружения анти-бот системами Vinted.

**Ключевые особенности:**
- ✅ 72 параллельных воркера с уникальными токенами
- ✅ **Pre-warming токенов** - мгновенный старт всех воркеров одновременно
- ✅ Автоматическая ротация 196 прокси
- ✅ Многоуровневая система защиты от бана
- ✅ Реалтайм мониторинг через Web UI
- ✅ **6-уровневая система редеплоя** (GraphQL → CLI → HTTP → Webhook → SIGTERM → Fake)
- ✅ **Healthcheck** для предотвращения CrashLoopBackOff
- ✅ Динамическая конфигурация без перезапуска

**🔥 Критические изменения от 06.10.2025:**
- ❌ Убран staggered start (задержки между воркерами)
- ✅ Добавлен pre-warming токенов (все токены создаются ДО старта)
- ✅ Воркеры стартуют МГНОВЕННО (start_delay=0)
- ✅ Задержка между находками = ТОЛЬКО Query Refresh Delay (60 сек)
- ✅ `refresh_delay` перенесен ДО try-except (исправлен undefined bug)
- ✅ `clear_item_queue()` обрабатывает ВСЕ элементы (было 1 → стало до 100)
- ✅ Redeploy через os._exit(1) включен по умолчанию
- ✅ Healthcheck endpoint (/health) для Railway мониторинга
- ✅ railway.json с restartPolicy (БЕЗ startCommand!)

**Система готова к продакшену и обеспечивает стабильную работу 24/7!** 🚀
