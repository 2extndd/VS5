-- Migration: Fix price column type from BIGINT to DECIMAL
-- Date: 2025-08-05
-- Issue: PostgreSQL BIGINT cannot store decimal values like "15.0", "19.99"

-- Change price column type to DECIMAL to support decimal values
ALTER TABLE items ALTER COLUMN price TYPE DECIMAL USING price::DECIMAL;

-- Also fix other NUMERIC fields that might have the same issue
ALTER TABLE items ALTER COLUMN item TYPE DECIMAL USING item::DECIMAL;
ALTER TABLE items ALTER COLUMN timestamp TYPE DECIMAL USING timestamp::DECIMAL;
ALTER TABLE queries ALTER COLUMN last_item TYPE DECIMAL USING last_item::DECIMAL;