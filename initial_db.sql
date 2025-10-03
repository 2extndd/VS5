-- init_schema.sql
-- Initial Scheme

PRAGMA foreign_keys = ON;

/* ============================
   Tables
   ============================ */

-- Queries table
CREATE TABLE IF NOT EXISTS queries
(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    query     TEXT,
    last_item NUMERIC,
    query_name TEXT,
    thread_id INTEGER DEFAULT NULL
);

-- Items table
CREATE TABLE IF NOT EXISTS items
(
    item       NUMERIC,
    title      TEXT,
    price      NUMERIC,
    currency   TEXT,
    timestamp  NUMERIC,  -- When item was published on Vinted
    photo_url  TEXT,
    brand_title TEXT,
    query_id   INTEGER,
    found_at   NUMERIC,  -- When bot discovered this item
    FOREIGN KEY (query_id) REFERENCES queries (id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_items_timestamp ON items(timestamp);
CREATE INDEX IF NOT EXISTS idx_items_query_id ON items(query_id);
CREATE INDEX IF NOT EXISTS idx_items_found_at ON items(found_at);

-- Allowlist table
CREATE TABLE IF NOT EXISTS allowlist
(
    country TEXT
);

-- Parameters table
CREATE TABLE IF NOT EXISTS parameters
(
    key   TEXT PRIMARY KEY,
    value TEXT
);

/* ============================
   Initial data
   ============================ */

INSERT INTO parameters (key, value)
VALUES ('telegram_enabled', 'False'),
       ('telegram_token', ''),
       ('telegram_chat_id', ''),
       ('telegram_process_running', 'False'),

       -- RSS parameters removed

       ('version', '1.35'),
       ('github_url', 'https://github.com/Fuyucch1/Vinted-Notifications'),

      ('items_per_query', '20'),
      ('query_refresh_delay', '60'),

      ('proxy_list', ''),
       ('proxy_list_link', ''),
       ('check_proxies', 'False'),
       ('last_proxy_check_time', '0'),
       ('proxy_rotation_interval', '1'),
       
       ('last_redeploy_time', ''),
       ('redeploy_threshold_minutes', '4'),
       ('max_http_errors', '5'),
       
       ('vinted_api_requests', '0'),
       ('bot_start_time', '0');
