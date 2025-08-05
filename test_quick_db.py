#!/usr/bin/env python3
"""
Quick Database Test - проверка исправления цен
Тестирует подключение и добавление товаров с десятичными ценами
"""

import sys
import os
import time

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_quick_database():
    """Быстрая проверка БД"""
    print("🏃‍♂️ БЫСТРЫЙ ТЕСТ БАЗЫ ДАННЫХ")
    print("=" * 40)
    
    try:
        import db
        print("✅ Модуль db импортирован")
        
        # Test connection
        conn, db_type = db.get_db_connection()
        print(f"✅ Подключение к {db_type} успешно")
        conn.close()
        
        # Test if we have any queries
        queries = db.get_queries()
        print(f"📋 Найдено {len(queries)} запросов в БД")
        
        if not queries:
            print("⚠️  Нет запросов в БД - добавлю тестовый")
            db.add_query_to_db("https://www.vinted.de/catalog?order=newest_first&test_quick=true", "Quick Test")
            queries = db.get_queries()
            
        # Use first available query
        query_id = queries[0][0]
        print(f"📝 Использую query_id: {query_id}")
        
        # Test adding item with decimal price
        test_items = [
            ("quick_test_1", "Quick Test Item", 15.99, "EUR"),
            ("quick_test_2", "Another Test", 29.50, "USD"),
        ]
        
        print("\n💰 Тестирую добавление товаров с десятичными ценами...")
        
        for item_id, title, price, currency in test_items:
            timestamp = int(time.time())
            photo_url = f"https://example.com/{item_id}.jpg"
            
            try:
                db.add_item_to_db(
                    id=item_id,
                    title=title,
                    query_id=query_id, 
                    price=price,
                    timestamp=timestamp,
                    photo_url=photo_url,
                    currency=currency
                )
                print(f"   ✅ {title} - {price} {currency} добавлен")
                
            except Exception as e:
                print(f"   ❌ Ошибка добавления {title}: {e}")
                return False
        
        # Test retrieval
        print("\n📥 Проверяю получение товаров...")
        items = db.get_items(limit=5)
        
        if items:
            print(f"✅ Получено {len(items)} товаров:")
            for item in items[:3]:
                item_id, title, price, currency = item[0], item[1], item[2], item[3]
                print(f"   🛍️  {title}: {price} {currency}")
        else:
            print("⚠️  Товары не найдены")
            
        # Cleanup
        print("\n🧹 Очистка тестовых данных...")
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("DELETE FROM items WHERE item LIKE 'quick_test_%'")
            cursor.execute("DELETE FROM queries WHERE query LIKE '%test_quick=true%'")
            conn.commit()
            print("✅ Тестовые данные удалены")
        
        conn.close()
        
        print("\n🎉 БЫСТРЫЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"💥 ОШИБКА ТЕСТА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_quick_database()
    if not success:
        sys.exit(1)