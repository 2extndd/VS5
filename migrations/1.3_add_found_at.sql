-- Migration: Add found_at column to items table
-- This column stores when the bot discovered the item (vs timestamp which is when it was published on Vinted)

-- For SQLite
ALTER TABLE items ADD COLUMN found_at NUMERIC;

-- For PostgreSQL: same syntax works
-- ALTER TABLE items ADD COLUMN found_at NUMERIC;

-- Update existing items: set found_at = timestamp for old items (approximation)
UPDATE items SET found_at = timestamp WHERE found_at IS NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_items_timestamp ON items(timestamp);
CREATE INDEX IF NOT EXISTS idx_items_query_id ON items(query_id);
CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at);

