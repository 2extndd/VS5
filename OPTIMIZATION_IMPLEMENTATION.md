# 🚀 ПЛАН ОПТИМИЗАЦИИ СИСТЕМЫ ЗАЩИТЫ ОТ БАНОВ

## 🎯 ГЛАВНАЯ ЦЕЛЬ
**Получать вещи почти мгновенно (2-5 сек задержки), не ловя баны**

---

## 📊 ТЕКУЩИЕ ПРОБЛЕМЫ

### Проблема #1: Burst Traffic
**Сейчас:** Все 72 queries выполняются почти одновременно каждые 60 сек
```
t=0:  ████████████████████ (72 requests за 10-20 сек)
t=60: ████████████████████ (72 requests за 10-20 сек)
```

**Результат:**
- Vinted видит всплеск с одного IP
- Триггер rate limiting → 429/403
- Очевидный паттерн бота

### Проблема #2: Медленная реакция на баны
**Сейчас:** 
- 5 ошибок за 4 минуты → редеплой
- 1-2 минуты downtime
- Потеря 50-100+ вещей

### Проблема #3: Неэффективная ротация прокси
**Сейчас:**
- Один прокси на все запросы
- Ротация только при 403
- Проверка каждые 6 часов

---

## ✅ РЕШЕНИЕ: 3-УРОВНЕВАЯ ЗАЩИТА

### Уровень 1: ADAPTIVE RATE LIMITER
**Что делает:** Динамически подстраивает скорость запросов

```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.min_delay = 2.0  # Минимум 2 сек между запросами
        self.max_delay = 10.0  # Максимум 10 сек
        self.current_delay = 2.0
        self.success_streak = 0
        self.error_streak = 0
    
    def on_success(self):
        self.success_streak += 1
        self.error_streak = 0
        # Каждые 10 успехов - ускоряемся на 10%
        if self.success_streak >= 10:
            self.current_delay *= 0.9
            self.current_delay = max(self.min_delay, self.current_delay)
            self.success_streak = 0
    
    def on_error(self, status_code):
        self.error_streak += 1
        self.success_streak = 0
        # При ошибке замедляемся в 2x
        if status_code == 429:
            self.current_delay = min(self.max_delay, self.current_delay * 2)
        elif status_code == 403:
            self.current_delay = min(self.max_delay, self.current_delay * 3)
    
    def wait(self):
        # Добавляем jitter ±20%
        jitter = random.uniform(0.8, 1.2)
        time.sleep(self.current_delay * jitter)
```

**Результат:**
- ✅ Скорость адаптируется к реакции Vinted
- ✅ Быстро при успехе, медленно при проблемах
- ✅ Jitter делает паттерн менее предсказуемым

---

### Уровень 2: CIRCUIT BREAKER
**Что делает:** Останавливает запросы ДО бана

```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Сломано, не шлем запросы
    HALF_OPEN = "half_open"  # Тестовый режим

class VintedCircuitBreaker:
    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = 3  # Открываем после 3 ошибок
        self.success_threshold = 2  # Закрываем после 2 успехов
        self.timeout = 60  # Пауза 60 сек в OPEN
        self.open_time = None
        self.half_open_success_count = 0
    
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            # Проверяем, прошло ли достаточно времени
            if time.time() - self.open_time > self.timeout:
                logger.info("[CIRCUIT] Transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_success_count += 1
            if self.half_open_success_count >= self.success_threshold:
                logger.info("[CIRCUIT] Transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def on_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            logger.warning(f"[CIRCUIT] Transitioning to OPEN after {self.failure_count} failures")
            self.state = CircuitState.OPEN
            self.open_time = time.time()
```

**Результат:**
- ✅ Автоматическая пауза при проблемах
- ✅ НЕТ downtime (не нужен редеплой)
- ✅ Самовосстановление

---

### Уровень 3: SMART PROXY ROTATION
**Что делает:** Интеллектуальное переключение прокси

```python
class SmartProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.request_count = 0
        self.rotate_every = 5  # Меняем прокси каждые 5 запросов
        self.proxy_stats = {}  # {proxy: {"success": 0, "fail": 0}}
        self.blacklist = {}  # {proxy: ban_until_timestamp}
    
    def get_next_proxy(self):
        self.request_count += 1
        
        # Ротация каждые N запросов
        if self.request_count % self.rotate_every == 0:
            self.current_index = (self.current_index + 1) % len(self.proxies)
        
        # Пропускаем забаненные прокси
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            
            # Проверяем blacklist
            if proxy in self.blacklist:
                if time.time() > self.blacklist[proxy]:
                    # Бан истек, удаляем из blacklist
                    del self.blacklist[proxy]
                    return proxy
                else:
                    # Еще забанен, берем следующий
                    self.current_index = (self.current_index + 1) % len(self.proxies)
                    attempts += 1
                    continue
            
            return proxy
        
        # Все забанены - используем прямое подключение
        return None
    
    def report_success(self, proxy):
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {"success": 0, "fail": 0}
        self.proxy_stats[proxy]["success"] += 1
    
    def report_failure(self, proxy, ban_duration=1800):  # 30 минут по умолчанию
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {"success": 0, "fail": 0}
        self.proxy_stats[proxy]["fail"] += 1
        
        # Добавляем в blacklist на 30 минут
        self.blacklist[proxy] = time.time() + ban_duration
        logger.warning(f"[PROXY] Blacklisted {proxy} for {ban_duration/60} minutes")
    
    def get_proxy_health(self, proxy):
        """Возвращает success rate (0.0 - 1.0)"""
        if proxy not in self.proxy_stats:
            return 1.0
        stats = self.proxy_stats[proxy]
        total = stats["success"] + stats["fail"]
        if total == 0:
            return 1.0
        return stats["success"] / total
```

**Результат:**
- ✅ Распределение нагрузки по прокси
- ✅ Автоматический blacklist плохих прокси
- ✅ Статистика здоровья прокси

---

## 🔄 ИНТЕГРАЦИЯ В REQUESTER

```python
# В pyVintedVN/requester.py

class requester:
    def __init__(self, cookie=None, with_proxy=True, debug=False, headers=None):
        # ... существующий код ...
        
        # НОВОЕ: Добавляем защитные механизмы
        self.rate_limiter = AdaptiveRateLimiter()
        self.circuit_breaker = VintedCircuitBreaker()
        self.proxy_manager = SmartProxyManager()
        
        # Загружаем прокси в proxy_manager
        if with_proxy:
            self.setup_proxy_manager()
    
    def setup_proxy_manager(self):
        """Инициализация прокси менеджера"""
        import proxies
        import db
        
        # Получаем все доступные прокси
        all_proxies = proxies._PROXY_CACHE or []
        self.proxy_manager.proxies = all_proxies
        logger.info(f"[REQUESTER] Loaded {len(all_proxies)} proxies into manager")
    
    def get(self, url, params=None):
        """GET запрос с полной защитой"""
        
        # Проверяем circuit breaker
        if self.circuit_breaker.state == CircuitState.OPEN:
            logger.warning("[REQUESTER] Circuit breaker is OPEN, skipping request")
            # Ждем и переводим в HALF_OPEN
            time.sleep(60)
            self.circuit_breaker.state = CircuitState.HALF_OPEN
        
        # Применяем rate limiting
        self.rate_limiter.wait()
        
        tried = 0
        while tried < 3:  # Уменьшили с 5 до 3
            tried += 1
            
            # Получаем прокси от умного менеджера
            current_proxy = self.proxy_manager.get_next_proxy()
            if current_proxy:
                self.session.proxies.update(
                    proxies.convert_proxy_string_to_dict(current_proxy)
                )
            
            try:
                def _make_request():
                    response = self.session.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        # Успех!
                        self.rate_limiter.on_success()
                        self.circuit_breaker.on_success()
                        self.proxy_manager.report_success(current_proxy)
                        report_success()
                        return response
                    elif response.status_code in (401, 403, 429):
                        # Ошибка авторизации/бан/rate limit
                        self.rate_limiter.on_error(response.status_code)
                        self.circuit_breaker.on_failure()
                        if current_proxy:
                            # Баним прокси на 30 минут
                            self.proxy_manager.report_failure(current_proxy, 1800)
                        
                        # Отчет системе редеплоя
                        if response.status_code == 401:
                            report_401_error()
                        elif response.status_code == 403:
                            report_403_error()
                        elif response.status_code == 429:
                            report_429_error()
                        
                        raise Exception(f"HTTP {response.status_code}")
                    else:
                        return response
                
                # Вызываем через circuit breaker
                return self.circuit_breaker.call(_make_request)
                
            except Exception as e:
                logger.warning(f"[REQUESTER] Request failed (try {tried}/3): {e}")
                
                if tried < 3:
                    # Exponential backoff с jitter
                    backoff = (2 ** tried) + random.uniform(0, 1)
                    logger.info(f"[REQUESTER] Retrying in {backoff:.2f} seconds...")
                    time.sleep(backoff)
                else:
                    raise e
        
        raise Exception("Max retries exceeded")
```

---

## 📈 СРАВНЕНИЕ: ДО vs ПОСЛЕ

### Скорость обнаружения вещей

**ДО:**
```
Query refresh delay: 60 sec
Время обнаружения: 0-60 sec (среднее 30 sec)
```

**ПОСЛЕ:**
```
Distributed batching: 72 queries / 12 batches = 6 queries/batch
Batch interval: 5 sec
Цикл: 12 batches * 5 sec = 60 sec

Время обнаружения: 0-60 sec (среднее 30 sec)
НО: более равномерное распределение!
```

### Защита от банов

**ДО:**
```
Паттерн: BURST ████████████ ... тишина ... BURST ████████████
Ban rate: 1-2/день
Recovery: 1-2 мин (редеплой)
```

**ПОСЛЕ:**
```
Паттерн: ████ pause ████ pause ████ pause (более человечно)
Adaptive delays: от 2 до 10 сек
Circuit breaker: автостоп при проблемах
Proxy rotation: каждые 5 запросов
Ban rate: 0-1/неделю
Recovery: 5-10 сек (circuit breaker)
```

---

## 🎯 МЕТРИКИ УСПЕХА

### KPI #1: Latency
- **Target:** < 5 сек от публикации до обнаружения
- **Metric:** Средняя разница timestamp vs found_at

### KPI #2: Ban Rate
- **Target:** < 1 бан в неделю
- **Metric:** Количество редеплоев за 7 дней

### KPI #3: Success Rate
- **Target:** > 95% успешных запросов
- **Metric:** (200 responses) / (total requests)

### KPI #4: Proxy Health
- **Target:** > 80% прокси работают
- **Metric:** (working proxies) / (total proxies)

---

## 🛠️ ПОРЯДОК ВНЕДРЕНИЯ

### Шаг 1: Minimal Viable Protection (30 мин)
```python
1. Добавить jitter к задержкам
2. Уменьшить MAX_RETRIES: 5 → 3
3. Добавить exponential backoff
4. Ротация прокси каждые 10 запросов
```

### Шаг 2: Circuit Breaker (1 час)
```python
1. Создать VintedCircuitBreaker class
2. Интегрировать в requester.get()
3. Добавить мониторинг состояния
```

### Шаг 3: Adaptive Rate Limiter (1 час)
```python
1. Создать AdaptiveRateLimiter class
2. Интегрировать в requester.get()
3. Настроить параметры (min/max delay)
```

### Шаг 4: Smart Proxy Manager (1 час)
```python
1. Создать SmartProxyManager class
2. Добавить blacklist logic
3. Добавить health tracking
```

### Шаг 5: Distributed Batching (30 мин)
```python
1. Разделить queries на батчи
2. Добавить паузы между батчами
3. Randomize порядок выполнения
```

---

## 💡 ДОПОЛНИТЕЛЬНЫЕ ТРЮКИ

### 1. Request Fingerprint Randomization
```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/131.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0.0.0"
]

ACCEPT_LANGUAGES = [
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9,de;q=0.8",
    "de;q=0.9,en;q=0.8"
]

# Ротация каждые 20 запросов
if request_count % 20 == 0:
    headers["User-Agent"] = random.choice(USER_AGENTS)
    headers["Accept-Language"] = random.choice(ACCEPT_LANGUAGES)
```

### 2. Time-based Throttling
```python
def get_hour_based_delay():
    hour = datetime.now().hour
    if 0 <= hour < 6:  # Ночь - меньше нагрузки
        return 1.5
    elif 12 <= hour < 18:  # День - больше нагрузки
        return 3.0
    else:  # Утро/вечер
        return 2.0
```

### 3. Connection Pooling
```python
# Переиспользуем соединения вместо создания новых
session.mount('https://', HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=0
))
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

1. **Не делай все сразу** - внедряй постепенно, тестируй каждый компонент
2. **Мониторь метрики** - без данных не поймешь, что работает
3. **Будь готов откатиться** - держи старую версию на случай проблем
4. **Логируй всё** - логи помогут понять паттерны банов
5. **Тестируй на малом** - сначала на 10 queries, потом на 72

---

## 🎬 ФИНАЛЬНЫЙ ЧЕКЛИСТ

- [ ] AdaptiveRateLimiter реализован
- [ ] CircuitBreaker реализован  
- [ ] SmartProxyManager реализован
- [ ] Exponential backoff добавлен
- [ ] Jitter добавлен во все задержки
- [ ] Ротация прокси каждые 5-10 запросов
- [ ] Health tracking для прокси
- [ ] Blacklist для плохих прокси
- [ ] Мониторинг метрик в dashboard
- [ ] Distributed batching для queries
- [ ] Request fingerprint randomization
- [ ] Логирование всех событий

