import sqlite3
import os
from traceback import print_exc

# Try to import psycopg2 for PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def get_db_connection():
    """Get database connection (PostgreSQL if available and configured, otherwise SQLite)"""
    # Check if PostgreSQL is configured via environment variables
    if POSTGRES_AVAILABLE and os.getenv('DATABASE_URL'):
        try:
            conn = psycopg2.connect(
                os.getenv('DATABASE_URL'),
                cursor_factory=RealDictCursor
            )
            return conn, 'postgresql'
        except Exception as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            print("Falling back to SQLite")
    
    # Default to SQLite
    conn = sqlite3.connect("vinted_notifications.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn, 'sqlite'


def create_or_update_db(db_path):
    """Create or update database from SQL file (works with both SQLite and PostgreSQL)"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # Read and modify SQL script for database compatibility
        with open(db_path, "r") as sql_file:
            sql_script = sql_file.read()
            
        if db_type == 'postgresql':
            # Convert SQLite-specific syntax to PostgreSQL
            sql_script = convert_sqlite_to_postgres(sql_script)
            
            # Execute statements one by one for PostgreSQL
            statements = sql_script.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    cursor.execute(statement)
        else:
            # SQLite can use executescript
            cursor.executescript(sql_script)

        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def convert_sqlite_to_postgres(sql_script):
    """Convert SQLite SQL to PostgreSQL compatible SQL"""
    # Remove SQLite-specific PRAGMA statements
    sql_script = sql_script.replace('PRAGMA foreign_keys = ON;', '')
    
    # Convert AUTOINCREMENT to SERIAL
    sql_script = sql_script.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    
    # Convert NUMERIC to appropriate PostgreSQL types
    sql_script = sql_script.replace('NUMERIC', 'BIGINT')
    
    # Convert IF NOT EXISTS for CREATE TABLE (PostgreSQL supports this)
    # But handle INSERT statements properly
    sql_script = sql_script.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
    
    # For PostgreSQL, we need to handle INSERT statements with ON CONFLICT
    # Split into statements and process each one
    statements = []
    for statement in sql_script.split(';'):
        statement = statement.strip()
        if statement:
            # Handle INSERT INTO parameters specifically
            if 'INSERT INTO parameters' in statement and 'ON CONFLICT' not in statement:
                # Add ON CONFLICT for parameters table which has PRIMARY KEY
                statement = statement.replace(
                    'INSERT INTO parameters (key, value) VALUES',
                    'INSERT INTO parameters (key, value) VALUES'
                ) + ' ON CONFLICT (key) DO NOTHING'
            statements.append(statement)
    
    return ';\n'.join(statements) + ';'


# Legacy function name for compatibility
def create_or_update_sqlite_db(db_path):
    """Legacy function name - redirects to create_or_update_db"""
    return create_or_update_db(db_path)


def is_item_in_db_by_id(id):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("SELECT COUNT(*) FROM items WHERE item=%s", (id,))
        else:
            cursor.execute("SELECT COUNT() FROM items WHERE item=?", (id,))
            
        result = cursor.fetchone()
        if db_type == 'postgresql':
            return result[0] > 0
        else:
            return result[0] > 0
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def get_last_timestamp(query_id):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("SELECT last_item FROM queries WHERE id=%s", (query_id,))
        else:
            cursor.execute("SELECT last_item FROM queries WHERE id=?", (query_id,))
            
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def update_last_timestamp(query_id, timestamp):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("UPDATE queries SET last_item=%s WHERE id=%s", (timestamp, query_id))
        else:
            cursor.execute("UPDATE queries SET last_item=? WHERE id=?", (timestamp, query_id))
            
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def add_item_to_db(id, title, query_id, price, timestamp, photo_url, currency="EUR"):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            # Insert into db the id and the query_id related to the item
            cursor.execute(
                "INSERT INTO items (item, title, price, currency, timestamp, photo_url, query_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (id, title, price, currency, timestamp, photo_url, query_id))
            # Update the last item for the query
            cursor.execute("UPDATE queries SET last_item=%s WHERE id=%s", (timestamp, query_id))
        else:
            # Insert into db the id and the query_id related to the item
            cursor.execute(
                "INSERT INTO items (item, title, price, currency, timestamp, photo_url, query_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (id, title, price, currency, timestamp, photo_url, query_id))
            # Update the last item for the query
            cursor.execute("UPDATE queries SET last_item=? WHERE id=?", (timestamp, query_id))
            
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_queries():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # Try to get with thread_id, fall back to without it for backward compatibility
        try:
            if db_type == 'postgresql':
                cursor.execute("SELECT id, query, last_item, query_name, thread_id FROM queries")
            else:
                cursor.execute("SELECT id, query, last_item, query_name, thread_id FROM queries")
        except:
            # Fallback for databases without thread_id column
            if db_type == 'postgresql':
                cursor.execute("SELECT id, query, last_item, query_name, NULL as thread_id FROM queries")
            else:
                cursor.execute("SELECT id, query, last_item, query_name, NULL as thread_id FROM queries")
            
        return cursor.fetchall()
    except Exception:
        print_exc()
        return []
    finally:
        if conn:
            conn.close()


def is_query_in_db(processed_query):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("SELECT COUNT(*) FROM queries WHERE query = %s", (processed_query,))
        else:
            cursor.execute("SELECT COUNT() FROM queries WHERE query = ?", (processed_query,))
            
        result = cursor.fetchone()
        return result[0] > 0
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def add_query_to_db(query, name=None, thread_id=None):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # Check if thread_id column exists
        try:
            if db_type == 'postgresql':
                if name:
                    cursor.execute("INSERT INTO queries (query, last_item, query_name, thread_id) VALUES (%s, NULL, %s, %s)", 
                                 (query, name, thread_id))
                else:
                    cursor.execute("INSERT INTO queries (query, last_item, thread_id) VALUES (%s, NULL, %s)", 
                                 (query, thread_id))
            else:
                if name:
                    cursor.execute("INSERT INTO queries (query, last_item, query_name, thread_id) VALUES (?, NULL, ?, ?)", 
                                 (query, name, thread_id))
                else:
                    cursor.execute("INSERT INTO queries (query, last_item, thread_id) VALUES (?, NULL, ?)", 
                                 (query, thread_id))
        except:
            # Fallback for databases without thread_id column
            if db_type == 'postgresql':
                if name:
                    cursor.execute("INSERT INTO queries (query, last_item, query_name) VALUES (%s, NULL, %s)", (query, name))
                else:
                    cursor.execute("INSERT INTO queries (query, last_item) VALUES (%s, NULL)", (query,))
            else:
                if name:
                    cursor.execute("INSERT INTO queries (query, last_item, query_name) VALUES (?, NULL, ?)", (query, name))
                else:
                    cursor.execute("INSERT INTO queries (query, last_item) VALUES (?, NULL)", (query,))
                    
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def update_query_thread_id(query_id, thread_id):
    """Update thread_id for a specific query"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("UPDATE queries SET thread_id=%s WHERE id=%s", (thread_id, query_id))
        else:
            cursor.execute("UPDATE queries SET thread_id=? WHERE id=?", (thread_id, query_id))
            
        conn.commit()
        return True
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def remove_query_from_db(query_number):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            # Get the query and its ID based on the row number
            cursor.execute("""
                SELECT id, query FROM (
                    SELECT id, query, ROW_NUMBER() OVER (ORDER BY id) rn 
                    FROM queries
                ) t WHERE rn=%s
            """, (query_number,))
            query_result = cursor.fetchone()
            
            if query_result:
                query_id = query_result[0]
                # Delete items associated with this query using query_id
                cursor.execute("DELETE FROM items WHERE query_id=%s", (query_id,))
                # Delete the query
                cursor.execute("DELETE FROM queries WHERE id=%s", (query_id,))
                conn.commit()
        else:
            # Get the query and its ID based on the row number
            query_string = f"SELECT id, query, rowid FROM (SELECT id, query, rowid, ROW_NUMBER() OVER (ORDER BY ROWID) rn FROM queries) t WHERE rn={query_number}"
            cursor.execute(query_string)
            query_result = cursor.fetchone()
            if query_result:
                query_id, query_text, rowid = query_result
                # Delete items associated with this query using query_id
                cursor.execute("DELETE FROM items WHERE query_id=?", (query_id,))
                # Delete the query
                cursor.execute("DELETE FROM queries WHERE ROWID=?", (rowid,))
                conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def remove_all_queries_from_db():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        # Delete all items first to maintain foreign key integrity
        cursor.execute("DELETE FROM items")
        # Then delete all queries
        cursor.execute("DELETE FROM queries")
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def clear_all_items():
    """Clear all items from the database while keeping queries"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items")
        # Reset last_item timestamp for all queries
        cursor.execute("UPDATE queries SET last_item = NULL")
        conn.commit()
        return True
    except Exception:
        print_exc()
        return False
    finally:
        if conn:
            conn.close()


def add_to_allowlist(country):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("INSERT INTO allowlist VALUES (%s)", (country,))
        else:
            cursor.execute("INSERT INTO allowlist VALUES (?)", (country,))
            
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def remove_from_allowlist(country):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("DELETE FROM allowlist WHERE country=%s", (country,))
        else:
            cursor.execute("DELETE FROM allowlist WHERE country=?", (country,))
            
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_allowlist():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM allowlist")
        # Get list of countries
        countries = [country[0] for country in cursor.fetchall()]
        # Return 0 if there are no countries in the allowlist
        if not countries:
            return 0
        return countries
    finally:
        if conn:
            conn.close()


def clear_allowlist():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM allowlist")
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_parameter(key):
    """Get parameter from database, with environment variable fallback"""
    # Check environment variables first for sensitive data
    env_mapping = {
        'telegram_token': 'TELEGRAM_BOT_TOKEN',
        'telegram_chat_id': 'TELEGRAM_CHAT_ID'
    }
    
    if key in env_mapping:
        env_value = os.getenv(env_mapping[key])
        if env_value:
            return env_value
    
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("SELECT value FROM parameters WHERE key=%s", (key,))
        else:
            cursor.execute("SELECT value FROM parameters WHERE key=?", (key,))
            
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def set_parameter(key, value):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("UPDATE parameters SET value=%s WHERE key=%s", (value, key))
        else:
            cursor.execute("UPDATE parameters SET value=? WHERE key=?", (value, key))
            
        conn.commit()
    except Exception:
        print_exc()
    finally:
        if conn:
            conn.close()


def get_all_parameters():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM parameters")
        params = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Override with environment variables if available
        env_mapping = {
            'telegram_token': 'TELEGRAM_BOT_TOKEN',
            'telegram_chat_id': 'TELEGRAM_CHAT_ID'
        }
        
        for param_key, env_key in env_mapping.items():
            env_value = os.getenv(env_key)
            if env_value:
                params[param_key] = env_value
                
        return params
    except Exception:
        print_exc()
        return {}
    finally:
        if conn:
            conn.close()


def get_items(limit=50, query=None):
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if query:
            if db_type == 'postgresql':
                # Get the query_id for the given query
                cursor.execute("SELECT id FROM queries WHERE query=%s", (query,))
                result = cursor.fetchone()
                if result:
                    query_id = result[0]
                    # Get items with the matching query_id
                    cursor.execute("""
                        SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url 
                        FROM items i JOIN queries q ON i.query_id = q.id 
                        WHERE i.query_id=%s ORDER BY i.timestamp DESC LIMIT %s
                    """, (query_id, limit))
                else:
                    return []
            else:
                # Get the query_id for the given query
                cursor.execute("SELECT id FROM queries WHERE query=?", (query,))
                result = cursor.fetchone()
                if result:
                    query_id = result[0]
                    # Get items with the matching query_id
                    cursor.execute(
                        "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url FROM items i JOIN queries q ON i.query_id = q.id WHERE i.query_id=? ORDER BY i.timestamp DESC LIMIT ?",
                        (query_id, limit))
                else:
                    return []
        else:
            if db_type == 'postgresql':
                # Join with queries table to get the query text
                cursor.execute("""
                    SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url 
                    FROM items i JOIN queries q ON i.query_id = q.id 
                    ORDER BY i.timestamp DESC LIMIT %s
                """, (limit,))
            else:
                # Join with queries table to get the query text
                cursor.execute(
                    "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url FROM items i JOIN queries q ON i.query_id = q.id ORDER BY i.timestamp DESC LIMIT ?",
                    (limit,))
                    
        return cursor.fetchall()
    except Exception:
        print_exc()
        return []
    finally:
        if conn:
            conn.close()


def get_total_items_count():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items")
        return cursor.fetchone()[0]
    except Exception:
        print_exc()
        return 0
    finally:
        if conn:
            conn.close()


def get_total_queries_count():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM queries")
        return cursor.fetchone()[0]
    except Exception:
        print_exc()
        return 0
    finally:
        if conn:
            conn.close()


def get_last_found_item():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("""
                SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url 
                FROM items i JOIN queries q ON i.query_id = q.id 
                ORDER BY i.timestamp DESC LIMIT 1
            """)
        else:
            cursor.execute(
                "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url FROM items i JOIN queries q ON i.query_id = q.id ORDER BY i.timestamp DESC LIMIT 1")
                
        return cursor.fetchone()
    except Exception:
        print_exc()
        return None
    finally:
        if conn:
            conn.close()


def get_items_per_day():
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        # Get total items
        cursor.execute("SELECT COUNT(*) FROM items")
        total_items = cursor.fetchone()[0]

        if total_items == 0:
            return 0

        # Get earliest and latest timestamps
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM items")
        min_timestamp, max_timestamp = cursor.fetchone()

        # Calculate number of days (add 1 to include both start and end days)
        import datetime
        min_date = datetime.datetime.fromtimestamp(min_timestamp).date()
        max_date = datetime.datetime.fromtimestamp(max_timestamp).date()
        days_diff = (max_date - min_date).days + 1

        # Ensure at least 1 day to avoid division by zero
        days_diff = max(1, days_diff)

        # Calculate items per day
        return round(total_items / days_diff, 1)
    except Exception:
        print_exc()
        return 0
    finally:
        if conn:
            conn.close()