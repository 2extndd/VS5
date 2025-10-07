# 🔐 Token + Proxy Binding System

## 🎯 Концепция

**Токен и Прокси живут вместе как неразрывная пара!**

```
┌──────────────────────────┐
│  Token A  +  Proxy X     │ ← Создаются вместе
│  (одна пара)             │ ← Живут вместе
└──────────────────────────┘ ← Умирают вместе
```

---

## 🚀 Как работает система

### 1️⃣ **При старте бота**

```
Token Pool создает 72 пары (Token + Proxy):

Worker 0  → Token #1  + Proxy #23  (IP: 1.2.3.4)
Worker 1  → Token #2  + Proxy #67  (IP: 5.6.7.8)
Worker 2  → Token #3  + Proxy #12  (IP: 9.1.2.3)
...
Worker 71 → Token #72 + Proxy #88  (IP: 10.11.12.13)
```

**Каждый worker получает свою уникальную пару!**

---

### 2️⃣ **Автоматическая ротация (каждые 5 сканов)**

```python
Worker 0:
  Scan 1 → Token #1 + Proxy #23 ✅
  Scan 2 → Token #1 + Proxy #23 ✅
  Scan 3 → Token #1 + Proxy #23 ✅
  Scan 4 → Token #1 + Proxy #23 ✅
  Scan 5 → Token #1 + Proxy #23 ✅
  
  🔄 AUTO-ROTATION (профилактика)
  
  Scan 6 → Token #73 + Proxy #45 ✅ (новая пара!)
  Scan 7 → Token #73 + Proxy #45 ✅
  ...
```

**Почему каждые 5 сканов?**
- Профилактика против накопления ошибок
- Регулярное обновление "цифрового следа"
- Vinted видит: "Обычная ротация пользователей" ✅

---

### 3️⃣ **При ошибке (агрессивная замена)**

```python
Worker 0:
  Scan 1 → Token #1 + Proxy #23 → HTTP 403 ❌
  
  🔄 IMMEDIATE RETRY #1 (новая пара!)
  Retry 1 → Token #74 + Proxy #56 → HTTP 403 ❌
  
  🔄 IMMEDIATE RETRY #2 (еще новая пара!)
  Retry 2 → Token #75 + Proxy #89 → HTTP 200 ✅
  
  Success! Продолжаем с Token #75 + Proxy #89
```

**Почему новая пара при каждом retry?**
- Если проблема в прокси → новый прокси поможет
- Если проблема в токене → новый токен поможет
- Если проблема в паре → новая пара точно поможет!
- Агрессивная стратегия для быстрого восстановления

---

### 4️⃣ **Прокси НЕ меняется при запросе**

```python
# ❌ БЫЛО (плохо):
def search(url):
    proxy = get_random_proxy()  # Случайный прокси каждый раз!
    session.proxies.update(proxy)  # Токен прыгает между IP
    response = session.get(url)

# ✅ СТАЛО (правильно):
def search(url):
    # Прокси уже установлен в session при создании пары
    # НЕ трогаем его!
    response = session.get(url)
```

**Почему это важно?**
- Vinted видит: "Токен всегда с одного IP" ✅
- Выглядит как настоящий пользователь ✅
- Никаких подозрительных прыжков между IP ✅

---

## 📊 Полный жизненный цикл

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: BOT START                                           │
├─────────────────────────────────────────────────────────────┤
│ TokenPool создает 72+ пары в параллель (10 секунд):         │
│   Pair 0:  Token #1  + Proxy #23  (IP: 1.2.3.4)            │
│   Pair 1:  Token #2  + Proxy #67  (IP: 5.6.7.8)            │
│   ...                                                        │
│   Pair 71: Token #72 + Proxy #88  (IP: 10.11.12.13)        │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: NORMAL OPERATION                                    │
├─────────────────────────────────────────────────────────────┤
│ Worker 0:                                                    │
│   Scan 1 → Token #1 + Proxy #23 → Success ✅                │
│   Sleep 60s                                                  │
│   Scan 2 → Token #1 + Proxy #23 → Success ✅                │
│   Sleep 60s                                                  │
│   Scan 3 → Token #1 + Proxy #23 → Success ✅                │
│   Sleep 60s                                                  │
│   Scan 4 → Token #1 + Proxy #23 → Success ✅                │
│   Sleep 60s                                                  │
│   Scan 5 → Token #1 + Proxy #23 → Success ✅                │
│   (5 сканов completed!)                                     │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: AUTO-ROTATION (every 5 scans)                      │
├─────────────────────────────────────────────────────────────┤
│ Worker 0:                                                    │
│   🔄 Scan counter = 5 → AUTO-ROTATION triggered             │
│   Create fresh pair: Token #73 + Proxy #45 (IP: 2.3.4.5)   │
│   Reset scan counter to 0                                   │
│   Scan 6 → Token #73 + Proxy #45 → Success ✅               │
│   (starting new rotation cycle)                             │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: ERROR RECOVERY (403/401)                           │
├─────────────────────────────────────────────────────────────┤
│ Worker 0:                                                    │
│   Scan 7 → Token #73 + Proxy #45 → HTTP 403 ❌              │
│   🔄 IMMEDIATE RETRY #1:                                     │
│      Create fresh pair: Token #74 + Proxy #56               │
│      Retry → HTTP 403 ❌                                     │
│   🔄 IMMEDIATE RETRY #2:                                     │
│      Create fresh pair: Token #75 + Proxy #89               │
│      Retry → HTTP 200 ✅                                     │
│   SUCCESS! Continue with Token #75 + Proxy #89              │
│   Reset scan counter to 0 (new pair = new cycle)            │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: CONTINUE NORMALLY                                   │
├─────────────────────────────────────────────────────────────┤
│ Worker 0:                                                    │
│   Scan 8  → Token #75 + Proxy #89 → Success ✅              │
│   Scan 9  → Token #75 + Proxy #89 → Success ✅              │
│   Scan 10 → Token #75 + Proxy #89 → Success ✅              │
│   ...                                                        │
│   (cycle continues until next rotation or error)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Преимущества новой системы

### ✅ **Стабильность**
- Каждый токен живет с ОДНИМ IP
- Vinted видит "нормального пользователя"
- Меньше банов!

### ✅ **Профилактика**
- Автоматическая ротация каждые 5 сканов
- Не ждем пока токен умрет
- Проактивное обновление

### ✅ **Быстрое восстановление**
- При ошибке → новая пара СРАЗУ
- До 3 попыток подряд
- Агрессивная замена

### ✅ **Использование всех прокси**
- 100 residential прокси = 100 "пользователей"
- Каждый прокси активно используется
- Ротация распределяет нагрузку

---

## 📝 Технические детали

### TokenSession (обновлен)

```python
class TokenSession:
    def __init__(self, session_id, session, access_token, user_agent, proxy):
        self.session_id = session_id
        self.session = session
        self.access_token = access_token
        self.user_agent = user_agent
        self.proxy = proxy  # ← НОВОЕ: прокси привязан к токену
        self.scan_count = 0  # ← НОВОЕ: счетчик для ротации
        self.created_at = time.time()
        self.request_count = 0
        self.error_count = 0
        self.is_valid = True
    
    def needs_rotation(self, rotation_interval=5):
        """Проверка: нужна ли ротация?"""
        return self.scan_count >= rotation_interval
    
    def increment_scan(self):
        """Инкремент счетчика сканов"""
        self.scan_count += 1
```

### TokenPool.create_fresh_pair() (новый метод)

```python
def create_fresh_pair(self, worker_index):
    """
    Создать свежую пару Token + Proxy для worker'а
    
    Используется для:
    - Автоматической ротации (каждые 5 сканов)
    - Восстановления при ошибках (immediate retry)
    """
    proxy = get_random_proxy()  # Случайный прокси из пула
    session = self._create_new_session_with_proxy(proxy)
    
    # Заменяем старую пару новой
    self.sessions[worker_index] = session
    return session
```

### Worker логика (обновлена)

```python
while True:
    # 1. Проверка: нужна ли автоматическая ротация?
    if token_session.needs_rotation(rotation_interval=5):
        token_session = token_pool.create_fresh_pair(worker_index)
        vinted = Vinted(session=token_session.session)
    
    # 2. Сканирование
    search_result = vinted.items.search(url)
    
    # 3. Обработка результата
    if success:
        token_session.increment_scan()  # Счетчик: 1, 2, 3, 4, 5...
    elif error_403:
        # Агрессивная замена: новая пара для каждого retry
        for retry in range(3):
            token_session = token_pool.create_fresh_pair(worker_index)
            vinted = Vinted(session=token_session.session)
            retry_result = vinted.items.search(url)
            if success:
                break
```

---

## 🔍 Отличия от старой системы

### ❌ СТАРАЯ СИСТЕМА (плохо)

```
- Прокси менялся при каждом запросе
- Токен "прыгал" между разными IP
- Vinted видел подозрительное поведение
- Частые баны
- Residential прокси использовались неэффективно
```

### ✅ НОВАЯ СИСТЕМА (правильно)

```
- Прокси привязан к токену
- Токен всегда с одного IP
- Vinted видит нормальных пользователей
- Меньше банов
- Эффективное использование 100 прокси
- Автоматическая ротация для профилактики
- Агрессивная замена при ошибках
```

---

## 🚀 Результат

**С 100 residential прокси:**
- 72 активных "пользователя" одновременно
- Каждый с уникальным IP
- Автообновление каждые 5 сканов
- Быстрое восстановление при ошибках
- Максимальная стабильность!

**Это выглядит как 72 настоящих пользователя Vinted!** ✨

