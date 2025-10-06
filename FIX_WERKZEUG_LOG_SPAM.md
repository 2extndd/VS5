# 🔇 Исправление: Спам werkzeug логов

## Проблема

**Логи замусорены HTTP запросами от Web UI:**

```
INFO werkzeug 100.64.0.6 - - [06/Oct/2025 17:34:27] "GET /api/logs?offset=0&limit=100&level=all HTTP/1.1" 200
INFO werkzeug 100.64.0.5 - - [06/Oct/2025 17:34:26] "GET /api/logs?offset=0&limit=100&level=all HTTP/1.1" 200
INFO werkzeug 100.64.0.5 - - [06/Oct/2025 17:34:25] "GET /api/logs?offset=0&limit=100&level=all HTTP/1.1" 200
... (30+ записей за 7 секунд!)
```

**Это что значит?**
- `werkzeug` - WSGI веб-сервер Flask
- `GET /api/logs` - Запрос к API для получения логов
- `200` - HTTP статус код (успешно)

**Почему так много?**
1. Страница логов автоматически обновляется каждые 10 секунд
2. Возможно открыто несколько вкладок Web UI
3. Каждый запрос логируется → спам в логах

**Результат:** Реальные логи бота **тонут** в HTTP логах веб-сервера!

## Решение

### 1️⃣ Отключены verbose логи werkzeug

**Было:**
```python
app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
# Логируются ВСЕ HTTP запросы (INFO level)
```

**Стало:**
```python
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # Только ошибки!

app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
# HTTP 200/304 не логируются, только ошибки 4xx/5xx
```

### 2️⃣ Увеличен интервал автообновления логов

**Было:**
```javascript
setInterval(() => {
    fetchLogs();
}, 10000);  // Обновление каждые 10 секунд
```

**Стало:**
```javascript
setInterval(() => {
    fetchLogs();
}, 30000);  // Обновление каждые 30 секунд
```

## Результат

✅ **Логи больше не замусорены HTTP запросами**  
✅ **Нагрузка на сервер снижена в 3 раза** (30s вместо 10s)  
✅ **Видны только важные логи:** workers, API requests, новые вещи  

## Что теперь логируется?

**Логируется:**
- 🔍 Работа workers (сканирование queries)
- 📊 API запросы к Vinted
- ✅ Найденные новые вещи
- ⚠️ Ошибки 403/401/429
- ❌ HTTP ошибки веб-сервера (4xx/5xx)

**НЕ логируется:**
- ❌ GET /api/logs (успешные запросы к API)
- ❌ GET /api/stats (успешные запросы статистики)
- ❌ GET /static/* (загрузка CSS/JS)
- ❌ Любые другие HTTP 200/304 запросы

## Если нужны HTTP логи

Можно временно включить для отладки:

```python
# В vinted_notifications.py
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)  # Включить обратно
```

Или смотреть в Railway логах (там все запросы всё равно логируются на уровне инфраструктуры).

## Изменённые файлы

1. **`vinted_notifications.py`** - Отключены werkzeug INFO логи
2. **`web_ui_plugin/templates/logs.html`** - Интервал 10s → 30s

**Коммит:** `0a22ebd`

