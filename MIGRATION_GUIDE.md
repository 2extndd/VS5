# Migration Guide

## Version 1.3 - Add Item Discovery Delay Tracking

### What's New
- **New field `found_at`**: Tracks when the bot discovered each item
- **Delay calculation**: Shows time difference between item publication on Vinted and bot discovery
- **Database indexes**: Improved query performance

### Migration Steps

#### For Railway (PostgreSQL):

1. Connect to Railway database:
```bash
railway connect
```

2. Run the migration SQL:
```sql
-- Add found_at column
ALTER TABLE items ADD COLUMN found_at NUMERIC;

-- Update existing items (set found_at = timestamp as approximation)
UPDATE items SET found_at = timestamp WHERE found_at IS NULL;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_items_timestamp ON items(timestamp);
CREATE INDEX IF NOT EXISTS idx_items_query_id ON items(query_id);
CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at);
```

Or use the migration file:
```bash
cat migrations/1.3_add_found_at.sql | railway run psql
```

#### For SQLite (local):

```bash
sqlite3 vinted.db < migrations/1.3_add_found_at.sql
```

### What Changed

**Database Schema:**
- `items` table now has `found_at` column
- Added 3 indexes for better performance

**UI Changes:**
- Dashboard and Items pages now show delay badges (e.g., "+3 мин", "+1 час")
- Delay appears next to timestamp in colored badge

**Performance Improvements:**
- Database indexes speed up queries on large datasets
- Optimized SQL JOINs with proper column selection

### Notes
- Old items will have `found_at = timestamp` (approximation)
- New items will have accurate `found_at` timestamp from bot discovery time
- Delay is only shown when both timestamps are available

