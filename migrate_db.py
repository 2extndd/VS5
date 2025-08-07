#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление поля brand_title
"""
import db

def migrate():
    try:
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            # Проверяем есть ли уже поле brand_title
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'items' AND column_name = 'brand_title'
            """)
            
            if not cursor.fetchone():
                print("Adding brand_title column to PostgreSQL...")
                cursor.execute("ALTER TABLE items ADD COLUMN brand_title TEXT DEFAULT ''")
                conn.commit()
                print("✅ Migration completed successfully!")
            else:
                print("✅ Column brand_title already exists")
        else:
            # SQLite - проверяем структуру таблицы
            cursor.execute("PRAGMA table_info(items)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'brand_title' not in column_names:
                print("Adding brand_title column to SQLite...")
                cursor.execute("ALTER TABLE items ADD COLUMN brand_title TEXT DEFAULT ''")
                conn.commit()
                print("✅ Migration completed successfully!")
            else:
                print("✅ Column brand_title already exists")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()