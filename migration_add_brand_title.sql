-- Migration to add brand_title column to items table
-- Run this on PostgreSQL production database

-- Check if column already exists, if not - add it
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'items' AND column_name = 'brand_title') THEN
        ALTER TABLE items ADD COLUMN brand_title TEXT DEFAULT '';
        RAISE NOTICE 'Column brand_title added to items table';
    ELSE
        RAISE NOTICE 'Column brand_title already exists in items table';
    END IF;
END $$;