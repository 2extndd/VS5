#!/usr/bin/env python3
"""
Тест проверки запросов в БД
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
from logger import get_logger

logger = get_logger(__name__)

def test_queries_in_db():
    """Проверяем запросы в БД"""
    print("🔍 ТЕСТ ЗАПРОСОВ В БД...")
    
    # Получаем все запросы
    queries = db.get_queries()
    print(f"📊 Всего запросов в БД: {len(queries)}")
    
    if queries:
        print("📋 Запросы:")
        for i, query in enumerate(queries):
            print(f"  {i+1}. ID: {query[0]}, URL: {query[1][:50]}...")
    
    # Проверяем товары
    items = db.get_items(limit=10)
    print(f"\n📊 Товаров в БД: {len(items)}")
    
    if items:
        print("📋 Товары:")
        for i, item in enumerate(items):
            print(f"  {i+1}. ID: {item[0]}, Title: {item[1][:30]}..., Query_ID: {item[5] if len(item) > 5 else 'N/A'}")
    
    # Проверяем товары без JOIN
    print("\n🔍 ПРОВЕРКА ТОВАРОВ БЕЗ JOIN...")
    try:
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("SELECT item, title, price, currency, timestamp, query_id, photo_url FROM items ORDER BY timestamp DESC LIMIT 10")
        else:
            cursor.execute("SELECT item, title, price, currency, timestamp, query_id, photo_url FROM items ORDER BY timestamp DESC LIMIT 10")
            
        raw_items = cursor.fetchall()
        print(f"📊 Товаров без JOIN: {len(raw_items)}")
        
        for i, item in enumerate(raw_items):
            print(f"  {i+1}. ID: {item[0]}, Title: {item[1][:30]}..., Query_ID: {item[5]}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке без JOIN: {e}")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТА ЗАПРОСОВ...")
    print("=" * 60)
    
    try:
        test_queries_in_db()
        
        print("\n" + "=" * 60)
        print("🎉 ТЕСТ ЗАВЕРШЕН!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТЕ: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}") 