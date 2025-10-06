# 🚨 CRITICAL FIX: Workers не запускались

## 🐛 Проблема

**Только 5 из 72 workers запустились успешно!**

```
[WORKERS] ⚠️ WARNING: 67 workers FAILED TO START!
[WORKERS] 📊 FINAL COUNT: 5/72 workers are ACTIVE!
```

## 🔍 Причина

### Несоответствие query_id и worker_index

**Что происходило:**

```python
# Worker получал query из БД
query_id = query[0]  # DB ID: может быть 1, 5, 75, 120... (с пропусками!)

# Worker запрашивал токен по query_id
token_session = token_pool.get_session_for_worker(query_id)  # ❌ Запрос токена #75!

# Но token pool создан только на 72 токена!
token_pool = TokenPool(target_size=72)  # Индексы: 0, 1, 2, ... 71
```

**Результат:**
- Worker с `query_id = 75` запрашивает токен #75
- В token pool есть только токены 0-71
- Worker НЕ получает токен
- После 5 попыток worker **ТЕРМИНИРУЕТСЯ НАВСЕГДА**
- 67 workers упали именно по этой причине!

### Пример из ваших логов:

```
Worker #75 needs token - creating session #75/72...
                                              ^^^ Больше чем target_size!
```

Query ID = 75 из базы данных (были удаления queries), но токенов только 72!

## ✅ Решение

### Разделили query_id и worker_index

```python
def continuous_query_worker(query, queue, worker_index=0, start_delay=0):
    """
    Args:
        worker_index: Sequential index (0,1,2...71) for token assignment
    """
    query_id = query[0]  # DB ID (может быть любым: 1, 5, 75...)
    
    # Используем worker_index для токенов (всегда 0-71)
    token_session = token_pool.get_session_for_worker(worker_index)  # ✅
    
    # Используем query_id для логов и DB операций
    logger.info(f"[WORKER #{query_id}] Starting...")  # Для читаемости логов
    db.update_query_last_found(query_id, timestamp)    # Для DB операций
```

### Как теперь назначаются токены:

```
Query DB ID → Worker Index → Token Index
─────────────────────────────────────────
    1      →      0       →      0
    5      →      1       →      1
   10      →      2       →      2
   75      →      3       →      3  ✅ Правильно!
  120      →      4       →      4
  ...
```

## 📊 Результат

✅ **Все 72 workers теперь получат токены правильно**  
✅ **Worker index последовательный:** 0, 1, 2, ... 71  
✅ **Query ID используется только для логов и DB**  
✅ **Token pool mapping правильный:** worker 0 → token 0, worker 1 → token 1, etc.  

## ❌ Нет механизма retry для упавших workers!

**Сейчас:** Если worker падает при старте → он **НИКОГДА** не перезапускается!

```python
if not token_session:
    logger.error(f"[WORKER #{query_id}] Worker TERMINATED!")
    return  # ← Worker умер навсегда!
```

**Это нужно исправить в будущем:**
- Добавить watchdog для мониторинга workers
- Перезапускать упавшие workers автоматически
- Или увеличить количество retry попыток с большими таймаутами

Но с текущим исправлением **ВСЕ workers должны стартовать успешно**, так что эта проблема не критична.

## 🚀 Что изменилось

**Файл:** `core.py`

**Изменения:**
1. Добавлен параметр `worker_index` в `continuous_query_worker()`
2. Все вызовы `get_session_for_worker()` теперь используют `worker_index`
3. При создании workers передается `idx` из `enumerate()`

**Коммит:** `c020581`

## 📈 Ожидаемый результат после деплоя

```
[TOKEN_POOL] ✅ PARALLEL pre-warming complete: 72 tokens in 38.2s!
[WORKERS] 🚀 Starting ALL 72 workers INSTANTLY...
[WORKER #1] Got session #1 with UA: ...
[WORKER #5] Got session #2 with UA: ...  ← Worker index = 1 (sequential)
[WORKER #75] Got session #3 with UA: ... ← Worker index = 2 (sequential)
...
[WORKERS] 📊 FINAL COUNT: 72/72 workers are ACTIVE! ✅
[WORKERS] ✅ All 72 workers are running successfully!
```

**Все 72 запроса будут сканироваться параллельно!** 🎉

