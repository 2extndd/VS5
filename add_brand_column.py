#!/usr/bin/env python3
import os
import psycopg2

# Получаем DATABASE_URL из переменных окружения Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Добавляем колонку brand_title если её нет
        cursor.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name = 'items' AND column_name = 'brand_title') THEN
                    ALTER TABLE items ADD COLUMN brand_title TEXT DEFAULT '';
                    RAISE NOTICE 'Column brand_title added to items table';
                ELSE
                    RAISE NOTICE 'Column brand_title already exists';
                END IF;
            END $$;
        """)
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()
else:
    print("❌ DATABASE_URL not found")