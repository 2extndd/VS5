-- Migration from version 1.0.3 to 1.0.5
-- Add thread_id column to queries table for Telegram supergroup topics support

-- Add thread_id column to queries table
ALTER TABLE queries ADD COLUMN thread_id INTEGER DEFAULT NULL;

-- Update version
UPDATE parameters SET value = '1.0.5' WHERE key = 'version';

-- Add new environment-based configuration parameters
INSERT OR IGNORE INTO parameters (key, value) VALUES 
    ('use_env_config', 'True'),
    ('proxy_auth_format', 'user:pass@ip:port');