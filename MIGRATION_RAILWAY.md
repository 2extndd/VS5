# 🚀 МИГРАЦИЯ БД НА RAILWAY ДЛЯ СЧЕТЧИКА ЗАДЕРЖКИ

## ⚠️ ВАЖНО
Перед деплоем v1.35.2 нужно применить миграцию к базе данных на Railway!

---

## 📋 ЧТО ДЕЛАЕТ МИГРАЦИЯ

Добавляет колонку `found_at` в таблицу `items`:
- **found_at** - когда бот нашел вещь (timestamp)
- Позволяет вычислить разницу между публикацией на Vinted и обнаружением ботом
- Отображается как: `Date: 2025-10-01 15:37:54 (+3 минуты)`

---

## 🔧 КАК ПРИМЕНИТЬ МИГРАЦИЮ

### Вариант 1: Через Railway CLI (рекомендуется)

```bash
# 1. Подключиться к БД Railway
railway link -p 101cc62f-b314-41d1-9b55-d58ae5c371ea

# 2. Открыть psql консоль
railway run psql $DATABASE_URL

# 3. Применить миграцию
\i migrations/1.3_add_found_at.sql

# 4. Проверить что колонка добавлена
\d items

# 5. Выйти
\q
```

### Вариант 2: Через Railway Dashboard

1. Зайти в Railway проект: https://railway.app/project/101cc62f-b314-41d1-9b55-d58ae5c371ea
2. Открыть PostgreSQL сервис
3. Перейти в **Data** → **Query**
4. Скопировать и выполнить SQL из `migrations/1.3_add_found_at.sql`:

```sql
-- Add found_at column
ALTER TABLE items ADD COLUMN found_at NUMERIC;

-- Update existing items
UPDATE items SET found_at = timestamp WHERE found_at IS NULL;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_items_timestamp ON items(timestamp);
CREATE INDEX IF NOT EXISTS idx_items_query_id ON items(query_id);
CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at);
```

5. Нажать **Run Query**

### Вариант 3: Вручную через psql

```bash
# Получить DATABASE_URL из Railway
# Settings → Variables → DATABASE_URL

psql "postgresql://postgres:PASSWORD@HOST:PORT/railway"

# Вставить SQL из migrations/1.3_add_found_at.sql
# Нажать Enter
```

---

## ✅ ПРОВЕРКА

После применения миграции проверь:

```sql
-- Проверить структуру таблицы
\d items

-- Должна быть колонка found_at
-- Должны быть индексы idx_items_timestamp, idx_items_query_id, idx_items_found_at

-- Проверить что данные обновились
SELECT item, timestamp, found_at FROM items LIMIT 5;
```

**Ожидаемый результат:**
- Колонка `found_at` существует
- У старых записей `found_at = timestamp`
- У новых записей `found_at` будет время обнаружения ботом

---

## 🎯 ПОСЛЕ МИГРАЦИИ

1. **Редеплой бота** на Railway (автоматически после push)
2. **Проверь Web UI:**
   - Dashboard: должны появиться бейджи с задержкой
   - Items page: должны появиться бейджи с задержкой
3. **Формат отображения:**
   - `+15 сек` - меньше минуты
   - `+3 мин` - меньше часа
   - `+2 часа` - меньше суток
   - `+1 день` - больше суток

---

## 🐛 TROUBLESHOOTING

### Ошибка: "column found_at does not exist"
**Решение:** Миграция еще не применена, выполни шаги выше

### Ошибка: "column found_at already exists"
**Решение:** Миграция уже применена, пропусти ALTER TABLE

### Счетчик не показывается
**Причины:**
1. Миграция не применена
2. В старых записях found_at = timestamp (разница 0)
3. Нужно дождаться новых вещей

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

**До миграции:**
```
Date: 2025-10-01 15:37:54
```

**После миграции:**
```
Date: 2025-10-01 15:37:54 (+3 минуты)
```

---

## 💡 ПОЛЬЗА

1. **Мониторинг скорости:** Видишь насколько быстро бот находит новые вещи
2. **Оптимизация:** Можно настроить `query_refresh_delay` для лучшей производительности
3. **Конкурентное преимущество:** Знаешь точно на сколько ты быстрее других

---

**Версия:** 1.35.2  
**Статус:** ✅ Готово к применению  
**Обязательно:** ⚠️ ДА, без миграции бот не будет сохранять found_at

