# 🚀 Railway Auto-Redeploy System

## 📋 Описание

Система автоматического редеплоя Railway предназначена для решения проблем с 403 ошибками от Vinted путем автоматического перезапуска приложения на Railway, что помогает сбросить IP-адрес и восстановить подключение.

## ⚙️ Как работает

### 🎯 Принцип работы

1. **Мониторинг ошибок**: Система отслеживает все HTTP 403 ошибки от Vinted API
2. **Анализ паттернов**: Подсчитывает количество ошибок и время с первой ошибки
3. **Автоматический редеплой**: При достижении пороговых значений инициирует редеплой Railway
4. **Сброс состояния**: После успешного запроса сбрасывает счетчики ошибок

### 📊 Условия для автоматического редеплоя

- **Время**: 4 минуты с первой 403 ошибки
- **Количество ошибок**: Минимум 5 ошибок 403 подряд
- **Защита от спама**: Минимум 10 минут между редеплоями

## 🔧 Настройка

### 1. Переменные окружения

```bash
# Railway Project ID (автоматически определяется)
RAILWAY_PROJECT_ID=101cc62f-b314-41d1-9b55-d58ae5c371ea

# Railway API Token (опционально, для API метода)
RAILWAY_TOKEN=your_railway_token_here

# Railway Service ID (автоматически определяется)
RAILWAY_SERVICE_ID=your_service_id
```

### 2. Railway CLI

Убедитесь, что Railway CLI установлен и аутентифицирован:

```bash
# Установка Railway CLI
npm install -g @railway/cli

# Авторизация
railway login

# Проверка статуса
railway whoami
```

## 📈 Мониторинг

### Web Interface

Доступен на странице конфигурации: `/config`

**Показатели:**
- Количество 403 ошибок
- Время первой и последней ошибки
- Время последнего редеплоя
- Статус необходимости редеплоя

### API Endpoints

```bash
# Получить статус системы редеплоя
GET /redeploy_status

# Принудительный редеплой
POST /force_redeploy
```

### Пример ответа API

```json
{
  "error_403_count": 3,
  "first_403_time": "2025-08-06T15:30:00Z",
  "last_403_time": "2025-08-06T15:32:00Z",
  "last_redeploy_time": null,
  "redeploy_threshold_minutes": 4,
  "max_403_errors": 5,
  "time_since_first_403_seconds": 180,
  "redeploy_needed": false,
  "monitoring_available": true
}
```

## 🔄 Методы редеплоя

### 1. Railway API (Приоритетный)

Использует GraphQL API Railway для программного редеплоя:

```graphql
mutation serviceRedeploy($serviceId: String!) {
  serviceRedeploy(serviceId: $serviceId) {
    id
  }
}
```

### 2. Railway CLI (Fallback)

При недоступности API использует CLI команду:

```bash
railway redeploy --yes
```

## 📝 Логирование

Все события системы логируются с префиксом `[REDEPLOY]`:

```
[REDEPLOY] First 403 error detected at 2025-08-06 15:30:00
[REDEPLOY] 403 error #3 detected at 2025-08-06 15:32:00
[REDEPLOY] Redeploy conditions met:
[REDEPLOY] - Time since first 403: 0:04:15
[REDEPLOY] - Total 403 errors: 5
[REDEPLOY] - Initiating automatic redeploy...
[REDEPLOY] ✅ Railway redeploy initiated successfully!
```

## 🛠️ Интеграция в код

### Requester Integration

Система автоматически интегрирована в `pyVintedVN/requester.py`:

```python
# Сообщение о 403 ошибке
if response.status_code == 403:
    report_403_error()

# Сообщение об успешном запросе
if response.status_code == 200:
    report_success()
```

### Manual Usage

```python
from railway_redeploy import report_403_error, report_success, get_redeploy_status

# Сообщить о 403 ошибке
report_403_error()

# Сообщить об успешном запросе
report_success()

# Получить статус
status = get_redeploy_status()
```

## 🚨 Troubleshooting

### Проблемы с токеном Railway

```bash
# Проверить аутентификацию
railway whoami

# Переавторизоваться
railway logout
railway login
```

### Проблемы с Service ID

```bash
# Проверить статус проекта
railway status

# Получить список сервисов
railway service list
```

### Отладка

```python
# Включить отладочные логи
import logging
logging.getLogger('railway_redeploy').setLevel(logging.DEBUG)
```

## 📋 Файлы системы

- `railway_redeploy.py` - Основная логика системы редеплоя
- `railway_config.py` - Конфигурация и настройка переменных окружения
- `pyVintedVN/requester.py` - Интеграция с HTTP requester
- `web_ui_plugin/web_ui.py` - API endpoints для мониторинга
- `web_ui_plugin/templates/config.html` - Web интерфейс мониторинга

## ✅ Тестирование

### Проверка работы системы

1. Запустите приложение
2. Дождитесь 403 ошибок от Vinted
3. Проверьте логи на наличие сообщений `[REDEPLOY]`
4. Откройте `/config` для мониторинга статуса

### Принудительный тест

```bash
# Через веб-интерфейс
curl -X POST http://localhost:5000/force_redeploy

# Или используйте кнопку "Force Redeploy" на странице /config
```

---

## 🎯 Результат

После внедрения системы:
- ✅ Автоматическое восстановление при 403 ошибках
- ✅ Мониторинг в реальном времени
- ✅ Защита от частых редеплоев
- ✅ Fallback методы для надежности
- ✅ Полное логирование всех операций