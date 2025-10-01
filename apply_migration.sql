-- Apply this SQL on Railway PostgreSQL NOW!
-- This will enable the delay counter immediately

-- Add found_at column
ALTER TABLE items ADD COLUMN IF NOT EXISTS found_at NUMERIC;

-- Update existing items (set found_at = timestamp for old items)
UPDATE items SET found_at = timestamp WHERE found_at IS NULL;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at);

-- Verify it worked
SELECT COUNT(*) as total_items, 
       COUNT(found_at) as items_with_found_at 
FROM items;

