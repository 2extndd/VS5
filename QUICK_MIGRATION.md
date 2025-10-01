# 🚀 БЫСТРАЯ МИГРАЦИЯ - ВКЛЮЧИТЬ СЧЕТЧИК СЕЙЧАС!

## ⚡ ВАРИАНТ 1: Railway Dashboard (САМЫЙ ПРОСТОЙ)

1. **Открой:** https://railway.app/project/101cc62f-b314-41d1-9b55-d58ae5c371ea

2. **Найди PostgreSQL сервис** → кликни на него

3. **Перейди в Data → Query**

4. **Скопируй и вставь этот SQL:**

```sql
ALTER TABLE items ADD COLUMN IF NOT EXISTS found_at NUMERIC;
UPDATE items SET found_at = timestamp WHERE found_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at);
SELECT COUNT(*) FROM items WHERE found_at IS NOT NULL;
```

5. **Нажми "Run Query"**

6. **Готово!** Перезагрузи dashboard - счетчик появится! ✅

---

## ⚡ ВАРИАНТ 2: Railway CLI (если установлен)

```bash
# Подключиться к проекту
railway link -p 101cc62f-b314-41d1-9b55-d58ae5c371ea

# Выполнить миграцию
railway run psql $DATABASE_URL -f apply_migration.sql

# Готово!
```

---

## ⚡ ВАРИАНТ 3: Прямой psql (если есть доступ)

1. Получи DATABASE_URL из Railway (Settings → Variables)

2. Выполни:
```bash
psql "YOUR_DATABASE_URL" -f apply_migration.sql
```

---

## ✅ ПРОВЕРКА

После выполнения:

1. **Dashboard** - должны появиться бейджи: `(+3 мин)`
2. **Items page** - то же самое
3. **Новые вещи** - покажут реальную задержку

Формат: `Date: 2025-10-01 15:37:54 (+3 минуты)`

---

## 🆘 ЕСЛИ НЕ РАБОТАЕТ

1. Проверь что миграция выполнилась:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name='items' AND column_name='found_at';
   ```
   Должна вернуть: `found_at`

2. Проверь что данные есть:
   ```sql
   SELECT COUNT(*) FROM items WHERE found_at IS NOT NULL;
   ```
   Должно быть > 0

3. Перезагрузи страницу dashboard (Ctrl+F5)

---

**ДЕЛАЙ ПРЯМО СЕЙЧАС!** Это займет 30 секунд! ⚡
