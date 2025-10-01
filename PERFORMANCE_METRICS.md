# Performance Metrics System

## Обзор

Система измерения производительности для Vinted бота с детальным профилированием каждого этапа обработки.

## Компоненты

### 1. Performance Profiler (`performance_profiler.py`)
- Централизованная система сбора метрик
- Измерение времени на каждом этапе
- Агрегация статистики (min, avg, max)
- Автоматический расчет задержек

### 2. Интеграция в Core (`core.py`)
Измеряемые этапы:
- ⏱️ **Общее время цикла** - полный цикл обработки
- 📊 **DB операции** - получение queries и stats
- 🔍 **API запросы** - время запроса к Vinted
- ✅ **Проверка дубликатов** - поиск в БД
- 💾 **Сохранение в БД** - INSERT операции
- 🎯 **Item latency** - от публикации до обнаружения

### 3. HTTP Requests (`pyVintedVN/requester.py`)
- ⏱️ **Выбор прокси** - время на получение прокси
- 🌐 **HTTP request** - время запроса к API
- 📡 **Response parsing** - парсинг ответа

### 4. Web UI (`/performance`)
Интерактивный дашборд с:
- 📊 Ключевые метрики (карточки)
- 🔄 Processing Pipeline (таймлайн)
- 📈 Детальная таблица статистики
- 🎨 Визуализация распределения времени

## Метрики

### Основные показатели:

1. **Total Item Latency** (Полная задержка)
   - От публикации вещи на Vinted до обнаружения ботом
   - Критический показатель скорости работы

2. **API Response Time** (Время ответа API)
   - Время HTTP запроса к Vinted
   - Зависит от прокси и сетевой задержки

3. **DB Check Time** (Проверка дубликатов)
   - Время поиска item_id в базе данных
   - Оптимизируется индексами

4. **DB Insert Time** (Сохранение в БД)
   - Время INSERT операции
   - Включает обновление query last_found

### Дополнительные метрики:

- **Proxy Selection** - время выбора случайного прокси
- **Cycle Start → API Request** - подготовка к запросу
- **Response Parsing** - парсинг JSON ответа
- **Query Processing** - обработка каждого query

## Использование

### Просмотр метрик в Web UI

1. Откройте `/performance` в браузере
2. Автообновление каждые 10 секунд
3. Кнопка "Refresh" для немедленного обновления

### API Endpoint

```bash
GET /api/performance
```

Ответ:
```json
{
  "available": true,
  "statistics": {
    "total_latency": {
      "min_ms": 1234,
      "avg_ms": 2456,
      "max_ms": 5678,
      "count": 100,
      "total_s": 245.6
    },
    "api_request_to_response": {...},
    ...
  },
  "current_metrics": {...},
  "timestamp": "2025-10-01 15:30:45"
}
```

### Логи

Профилировщик пишет в логи:
```
[PERF] ⏱️ START: operation_name
[PERF] ⏹️ END: operation_name = 0.123s (123ms)
[PERF] 📊 METRIC: metric_name = 0.456s (456ms)
[PERF] 🎯 Item latency: 2.345s (2345ms)
[PERF] 🏁 Cycle completed in 5.678s
[PERF] ⚡ Item 12345 total processing: 0.089s

=== PERFORMANCE SUMMARY ===
Current Cycle Metrics:
  total_cycle_time                         5.678s (5678ms)
  query_1_api_call                        2.345s (2345ms)
  ...

Overall Statistics:
  total_latency:
    Min: 1.234s (1234ms)
    Avg: 2.456s (2456ms)
    Max: 5.678s (5678ms)
    Count: 100 samples
```

## Интерпретация результатов

### Идеальные показатели:
- ✅ Total Latency: < 3 секунд
- ✅ API Response: < 1 секунды
- ✅ DB Check: < 50 мс
- ✅ DB Insert: < 100 мс

### Проблемные значения:
- ⚠️ Total Latency > 5 секунд - медленное обнаружение
- ⚠️ API Response > 3 секунд - проблемы с прокси
- ⚠️ DB Check > 200 мс - нужны индексы
- ⚠️ DB Insert > 500 мс - перегрузка БД

## Оптимизация

### Если высокая API Response Time:
1. Проверьте качество прокси
2. Уменьшите `proxy_rotation_interval`
3. Увеличьте частоту проверки прокси

### Если высокая DB Check/Insert Time:
1. Проверьте индексы (idx_items_item)
2. Оптимизируйте запросы
3. Рассмотрите PostgreSQL connection pooling

### Если высокая Total Latency:
1. Уменьшите `items_per_query`
2. Увеличьте частоту циклов
3. Оптимизируйте все вышеперечисленное

## Архитектура Pipeline

```
┌──────────────────────────────────────────────────┐
│ 1. Цикл начинается                               │
│    ↓ (Proxy Selection)                           │
│ 2. Выбор случайного прокси из пула               │
│    ↓ (API Request)                                │
│ 3. HTTP GET запрос к Vinted API                  │
│    ↓ (Response Parsing)                           │
│ 4. Парсинг JSON ответа → Item объекты            │
│    ↓ (для каждого Item)                          │
│ 5. Проверка дубликата в БД                       │
│    ↓ (если новый)                                │
│ 6. Сохранение в БД + расчет latency              │
│    ↓                                              │
│ 7. Отправка в Telegram                           │
└──────────────────────────────────────────────────┘

Total Latency = (found_at timestamp) - (item timestamp)
```

## Changelog

### v1.36 (2025-10-01)
- ✨ Добавлена система измерения производительности
- 📊 Профилирование всех критических этапов
- 🎨 Web UI дашборд для метрик
- 📈 Агрегация статистики (min/avg/max)
- 🔍 Детальный анализ задержек

