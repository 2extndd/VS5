-- Migration: Add priority queries support
-- Version: 1.6.1 -> 1.7.0
-- Date: 2025-10-07

-- Add is_priority field to queries table
-- Priority queries get 3 workers scanning every 20 seconds
-- Normal queries get 1 worker scanning at default interval

ALTER TABLE queries ADD COLUMN IF NOT EXISTS is_priority BOOLEAN DEFAULT FALSE;

-- Optional: Set example priority queries (commented out by default)
-- UPDATE queries SET is_priority = TRUE WHERE id IN (1, 2);

-- Verify the migration
-- SELECT id, name, is_priority FROM queries;

