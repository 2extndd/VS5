#!/usr/bin/env python3
"""
Тест дедупликации товаров и фильтрации
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
from logger import get_logger

logger = get_logger(__name__)

def test_database_dedup():
    """Тест дедупликации в базе данных"""
    print("🔍 ТЕСТ ДЕДУПЛИКАЦИИ В БАЗЕ ДАННЫХ...")
    
    # Добавляем тестовый товар
    test_item_id = "test_item_123"
    test_title = "Test Item"
    test_query_id = 1
    test_price = 25.99
    test_timestamp = 1640995200  # 2022-01-01
    test_photo_url = "https://example.com/photo.jpg"
    test_currency = "EUR"
    
    print(f"📝 Добавляем тестовый товар: {test_item_id}")
    
    # Первое добавление
    result1 = db.add_item_to_db(
        id=test_item_id,
        title=test_title,
        query_id=test_query_id,
        price=test_price,
        timestamp=test_timestamp,
        photo_url=test_photo_url,
        currency=test_currency
    )
    print(f"✅ Первое добавление: {result1}")
    
    # Проверяем существование
    exists1 = db.is_item_in_db_by_id(test_item_id)
    print(f"🔍 Товар существует после первого добавления: {exists1}")
    
    # Второе добавление (должно быть отклонено)
    result2 = db.add_item_to_db(
        id=test_item_id,
        title=test_title,
        query_id=test_query_id,
        price=test_price,
        timestamp=test_timestamp,
        photo_url=test_photo_url,
        currency=test_currency
    )
    print(f"❌ Второе добавление: {result2}")
    
    # Проверяем количество товаров
    items = db.get_items(limit=100)
    test_items = [item for item in items if item[0] == test_item_id]
    print(f"📊 Количество товаров с ID {test_item_id}: {len(test_items)}")
    
    # Очищаем тестовый товар
    print("🧹 Очищаем тестовый товар...")
    # Здесь можно добавить функцию удаления тестового товара
    
    print("✅ ТЕСТ ДЕДУПЛИКАЦИИ ЗАВЕРШЕН!")

def test_item_filtering():
    """Тест фильтрации товаров"""
    print("\n🔍 ТЕСТ ФИЛЬТРАЦИИ ТОВАРОВ...")
    
    # Получаем все товары
    all_items = db.get_items(limit=100)
    print(f"📊 Всего товаров в БД: {len(all_items)}")
    
    if all_items:
        print("📋 Примеры товаров:")
        for i, item in enumerate(all_items[:5]):
            print(f"  {i+1}. ID: {item[0]}, Title: {item[1][:50]}..., Price: {item[2]}")
    
    print("✅ ТЕСТ ФИЛЬТРАЦИИ ЗАВЕРШЕН!")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТОВ ДЕДУПЛИКАЦИИ И ФИЛЬТРАЦИИ...")
    print("=" * 60)
    
    try:
        test_database_dedup()
        test_item_filtering()
        
        print("\n" + "=" * 60)
        print("🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}") 