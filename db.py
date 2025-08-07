import sqlite3
import os
from traceback import print_exc
from logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Try to import psycopg2 for PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def safe_get_result(result, index=0):
    """Safely get result from database query, handling different cursor types"""
    if result:
        try:
            return result[index]
        except (IndexError, KeyError, TypeError):
            # If result is not subscriptable or wrong format, return the result itself
            return result if index == 0 else None
    return None


def get_db_connection():
    """Get database connection (PostgreSQL if available and configured, otherwise SQLite)"""
    from logger import get_logger
    logger = get_logger(__name__)
    
    # Check if PostgreSQL is configured via environment variables
    if POSTGRES_AVAILABLE and os.getenv('DATABASE_URL'):
        try:
            logger.debug("Attempting to connect to PostgreSQL...")
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            logger.debug("Successfully connected to PostgreSQL")
            return conn, 'postgresql'
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}")
            logger.info("Falling back to SQLite")
    
    # Default to SQLite
    logger.debug("Using SQLite database")
    conn = sqlite3.connect("vinted_notifications.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn, 'sqlite'


def apply_migration(migration_path):
    """Apply a database migration"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        from logger import get_logger
        logger = get_logger(__name__)
        
        if not os.path.exists(migration_path):
            logger.warning(f"Migration file not found: {migration_path}")
            return False
            
        with open(migration_path, "r") as sql_file:
            migration_script = sql_file.read()
            
        logger.info(f"Applying migration: {migration_path}")
        
        if db_type == 'postgresql':
            # Split into individual statements
            statements = [stmt.strip() for stmt in migration_script.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
            
            for i, statement in enumerate(statements):
                try:
                    logger.info(f"Executing migration statement {i+1}: {statement[:100]}...")
                    cursor.execute(statement)
                    conn.commit()
                    logger.info(f"Migration statement {i+1} executed successfully")
                except Exception as e:
                    logger.error(f"Error executing migration statement {i+1}: {e}")
                    logger.error(f"Statement was: {statement}")
                    conn.rollback()
                    return False
        else:
            # For SQLite, execute the entire script
            cursor.executescript(migration_script)
            
        logger.info(f"Migration {migration_path} applied successfully")
        return True
        
    except Exception as e:
        from logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to apply migration {migration_path}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def create_or_update_db(db_path):
    """Create or update database from SQL file (works with both SQLite and PostgreSQL)"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # Read and modify SQL script for database compatibility
        with open(db_path, "r") as sql_file:
            sql_script = sql_file.read()
            
        from logger import get_logger
        logger = get_logger(__name__)
        logger.info(f"Database type: {db_type}")
        logger.info(f"Executing database creation script: {db_path}")
            
        if db_type == 'postgresql':
            # Convert SQLite-specific syntax to PostgreSQL
            statements = convert_sqlite_to_postgres(sql_script)
            logger.info("Converted SQL statements for PostgreSQL:")
            for i, stmt in enumerate(statements[:3]):  # Print first 3 statements
                logger.info(f"Statement {i+1}: {stmt[:100]}...")
            
            # Execute statements one by one for PostgreSQL
            for i, statement in enumerate(statements):
                if statement and not statement.startswith('--'):
                    try:
                        logger.info(f"Executing statement {i+1}/{len(statements)}: {statement[:100]}...")
                        cursor.execute(statement)
                        conn.commit()  # Commit after each statement for PostgreSQL
                        logger.info(f"Statement {i+1} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing statement {i+1}: {e}")
                        logger.error(f"Statement was: {statement}")
                        # Continue with next statement instead of raising
                        logger.info(f"Continuing with next statement...")
                        conn.rollback()  # Rollback failed transaction
                        
            # Apply critical migrations after schema creation
            logger.info("Applying price type migration for PostgreSQL...")
            apply_migration("migrations/fix_price_type.sql")
        else:
            # SQLite can use executescript
            cursor.executescript(sql_script)
            conn.commit()

        logger.info("Database creation/update completed successfully")
    except Exception as e:
        logger.error(f"Error in create_or_update_db: {e}")
        logger.error("Full traceback:", exc_info=True)
        if conn:
            conn.rollback()
        raise
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
    sql_script = sql_script.replace('NUMERIC', 'DECIMAL')
    
    # Convert INSERT OR IGNORE to INSERT with ON CONFLICT
    sql_script = sql_script.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
    
    # Split by semicolon while preserving multi-line statements
    lines = sql_script.split('\n')
    statements = []
    current_statement = ""
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('--'):
            current_statement += line + " "
            if line.endswith(';'):
                # End of statement
                statement = current_statement.strip().rstrip(';')
                if statement and len(statement) > 3:
                    statements.append(statement)
                current_statement = ""
    
    # Add any remaining statement
    if current_statement.strip():
        statement = current_statement.strip().rstrip(';')
        if statement and len(statement) > 3:
            statements.append(statement)
    
    # Process each statement for PostgreSQL compatibility
    processed_statements = []
    for statement in statements:
        # Handle multi-line INSERT INTO parameters VALUES
        if ('INSERT INTO parameters' in statement and 
            'VALUES' in statement and 
            'ON CONFLICT' not in statement):
            # For parameters table with PRIMARY KEY, add ON CONFLICT
            statement = statement + ' ON CONFLICT (key) DO NOTHING'
        
        processed_statements.append(statement)
    
    return processed_statements  # Return as list, not joined string


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
            cursor.execute("SELECT COUNT(*) FROM items WHERE item=?", (id,))
            
        result = cursor.fetchone()
        count = safe_get_result(result, 0)
        return count > 0 if count is not None else False
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
        return safe_get_result(result, 0)
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
    from logger import get_logger
    logger = get_logger(__name__)
    
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        logger.info(f"Attempting to add item {id} to database (query_id: {query_id})")
        
        # Check if item already exists in database
        if is_item_in_db_by_id(id):
            logger.info(f"Item {id} already exists in database, skipping...")
            return False
        else:
            logger.info(f"Item {id} is new, proceeding with database insertion...")
        
        # Check database size limits (prevent excessive growth)
        cursor.execute("SELECT COUNT(*) FROM items")
        total_items = cursor.fetchone()[0]
        MAX_ITEMS = 50000  # Limit to 50K items to prevent database bloat
        
        if total_items >= MAX_ITEMS:
            logger.warning(f"Database has reached maximum items limit ({MAX_ITEMS}). Consider cleaning old items.")
            # Clean old items (keep only recent 30000)
            if db_type == 'postgresql':
                cursor.execute("DELETE FROM items WHERE item IN (SELECT item FROM items ORDER BY timestamp ASC LIMIT %s)", (total_items - 30000,))
            else:
                cursor.execute("DELETE FROM items WHERE item IN (SELECT item FROM items ORDER BY timestamp ASC LIMIT ?)", (total_items - 30000,))
            logger.info(f"Cleaned old items, keeping most recent 30000")
        
        # Convert price to float for DECIMAL compatibility
        try:
            price_decimal = float(price) if price is not None else 0.0
        except (ValueError, TypeError):
            logger.warning(f"Invalid price '{price}' for item {id}, using 0.0")
            price_decimal = 0.0
        
        if db_type == 'postgresql':
            # Insert into db the id and the query_id related to the item
            cursor.execute(
                "INSERT INTO items (item, title, price, currency, timestamp, photo_url, query_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (id, title, price_decimal, currency, timestamp, photo_url, query_id))
            # Update the last item for the query
            cursor.execute("UPDATE queries SET last_item=%s WHERE id=%s", (timestamp, query_id))
        else:
            # Insert into db the id and the query_id related to the item
            cursor.execute(
                "INSERT INTO items (item, title, price, currency, timestamp, photo_url, query_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (id, title, price_decimal, currency, timestamp, photo_url, query_id))
            # Update the last item for the query
            cursor.execute("UPDATE queries SET last_item=? WHERE id=?", (timestamp, query_id))
            
        conn.commit()
        logger.info(f"Successfully added item {id} to database with price {price_decimal}")
        return True
    except Exception as e:
        logger.error(f"Error adding item {id} to database: {e}")
        logger.error("Full traceback:", exc_info=True)
        if conn:
            conn.rollback()
        return False
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


def get_items_count_by_query(query_id):
    """Get count of items for a specific query"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("SELECT COUNT(*) FROM items WHERE query_id = %s", (query_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM items WHERE query_id = ?", (query_id,))
            
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception:
        print_exc()
        return 0
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
        count = safe_get_result(result, 0)
        return count > 0 if count is not None else False
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


def remove_query_from_db(query_id):
    """Remove query by ID (not row number)"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # Convert query_id to int if it's a string
        try:
            query_id = int(query_id)
        except (ValueError, TypeError):
            print(f"Invalid query_id: {query_id}")
            return
        
        if db_type == 'postgresql':
            # Delete items associated with this query first
            cursor.execute("DELETE FROM items WHERE query_id=%s", (query_id,))
            # Delete the query
            cursor.execute("DELETE FROM queries WHERE id=%s", (query_id,))
            conn.commit()
            print(f"Removed query with ID {query_id} from PostgreSQL database")
        else:
            # Delete items associated with this query first
            cursor.execute("DELETE FROM items WHERE query_id=?", (query_id,))
            # Delete the query
            cursor.execute("DELETE FROM queries WHERE id=?", (query_id,))
            conn.commit()
            print(f"Removed query with ID {query_id} from SQLite database")
            
    except Exception as e:
        print(f"Error removing query {query_id}: {e}")
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
        return safe_get_result(result, 0)
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


def get_database_stats():
    """Get database statistics for debugging"""
    from logger import get_logger
    logger = get_logger(__name__)
    
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Get total items count
        cursor.execute("SELECT COUNT(*) FROM items")
        stats['total_items'] = cursor.fetchone()[0]
        
        # Get items count per query
        if db_type == 'postgresql':
            cursor.execute("""
                SELECT q.query_name, COUNT(i.item) as item_count 
                FROM queries q 
                LEFT JOIN items i ON q.id = i.query_id 
                GROUP BY q.id, q.query_name
            """)
        else:
            cursor.execute("""
                SELECT q.query_name, COUNT(i.item) as item_count 
                FROM queries q 
                LEFT JOIN items i ON q.id = i.query_id 
                GROUP BY q.id, q.query_name
            """)
            
        stats['items_per_query'] = cursor.fetchall()
        
        # Get recent items (last 24 hours)
        import time
        twenty_four_hours_ago = time.time() - 86400
        
        if db_type == 'postgresql':
            cursor.execute("SELECT COUNT(*) FROM items WHERE timestamp > %s", (twenty_four_hours_ago,))
        else:
            cursor.execute("SELECT COUNT(*) FROM items WHERE timestamp > ?", (twenty_four_hours_ago,))
            
        stats['recent_items_24h'] = cursor.fetchone()[0]
        
        logger.info(f"Database stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
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
                    query_id = safe_get_result(result, 0)
                    # Get items with the matching query_id
                    if limit is None:
                        cursor.execute("""
                            SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url 
                            FROM items i JOIN queries q ON i.query_id = q.id 
                            WHERE i.query_id=%s ORDER BY i.timestamp DESC
                        """, (query_id,))
                    else:
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
                    query_id = safe_get_result(result, 0)
                    # Get items with the matching query_id
                    if limit is None:
                        cursor.execute(
                            "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url FROM items i JOIN queries q ON i.query_id = q.id WHERE i.query_id=? ORDER BY i.timestamp DESC",
                            (query_id,))
                    else:
                        cursor.execute(
                            "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url FROM items i JOIN queries q ON i.query_id = q.id WHERE i.query_id=? ORDER BY i.timestamp DESC LIMIT ?",
                            (query_id, limit))
                else:
                    return []
        else:
            if db_type == 'postgresql':
                # Join with queries table to get the query text
                if limit is None:
                    cursor.execute("""
                        SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url 
                        FROM items i JOIN queries q ON i.query_id = q.id 
                        ORDER BY i.timestamp DESC
                    """)
                else:
                    cursor.execute("""
                        SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url 
                        FROM items i JOIN queries q ON i.query_id = q.id 
                        ORDER BY i.timestamp DESC LIMIT %s
                    """, (limit,))
            else:
                # Join with queries table to get the query text
                if limit is None:
                    cursor.execute(
                        "SELECT i.item, i.title, i.price, i.currency, i.timestamp, q.query, i.photo_url FROM items i JOIN queries q ON i.query_id = q.id ORDER BY i.timestamp DESC")
                else:
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


def get_api_requests_count():
    """Get total API requests to Vinted since bot start"""
    try:
        vinted_requests = get_parameter('vinted_api_requests')
        return int(vinted_requests) if vinted_requests else 0
    except Exception:
        return 0


def increment_api_requests():
    """Increment API requests counter"""
    try:
        current_count = get_api_requests_count()
        set_parameter('vinted_api_requests', str(current_count + 1))
    except Exception:
        pass


def reset_api_requests():
    """Reset API requests counter (called on bot start)"""
    try:
        import time
        set_parameter('vinted_api_requests', '0')
        set_parameter('bot_start_time', str(int(time.time())))
    except Exception:
        pass


def get_bot_uptime():
    """Get bot uptime in human readable format"""
    try:
        start_time = get_parameter('bot_start_time')
        if not start_time:
            return "Unknown"
        
        import time
        uptime_seconds = int(time.time()) - int(start_time)
        
        if uptime_seconds < 60:
            return f"{uptime_seconds}s"
        elif uptime_seconds < 3600:
            return f"{uptime_seconds // 60}m"
        elif uptime_seconds < 86400:
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            return f"{days}d {hours}h"
    except Exception:
        return "Unknown"


def update_query_last_found(query_id, timestamp):
    """Update the last_item timestamp for a query (fixed field name)"""
    conn = None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        # Update the last_item field for the query (correct field name)
        if db_type == 'postgresql':
            cursor.execute("""
                UPDATE queries 
                SET last_item = %s 
                WHERE id = %s
            """, (timestamp, query_id))
        else:
            cursor.execute(
                "UPDATE queries SET last_item = ? WHERE id = ?",
                (timestamp, query_id))
        
        conn.commit()
        logger.info(f"Updated last_item for query {query_id} to timestamp {timestamp}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating query last_found: {e}")
        print_exc()
        return False
    finally:
        if conn:
            conn.close()