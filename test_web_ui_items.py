#!/usr/bin/env python3
"""
Тест добавления товаров в Web UI
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
import requests
import time
from logger import get_logger

logger = get_logger(__name__)

def test_add_items_to_db():
    """Добавляем тестовые товары в БД"""
    print("🔍 ТЕСТ ДОБАВЛЕНИЯ ТОВАРОВ В БД...")
    
    test_items = [
        {
            'id': 'web_test_1',
            'title': 'Test Item for Web UI 1',
            'query_id': 1,
            'price': 19.99,
            'timestamp': int(time.time()),
            'photo_url': 'https://images1.vinted.net/t/01_0050d_97Nn6hqaXXMZXwT5LcsFQkEx/f800/1754344834.jpeg',
            'currency': 'EUR'
        },
        {
            'id': 'web_test_2', 
            'title': 'Test Item for Web UI 2',
            'query_id': 1,
            'price': 29.50,
            'timestamp': int(time.time()),
            'photo_url': 'https://images1.vinted.net/t/01_01c6b_pbecDu37HxEhPkdQDFiZoTzD/f800/1754344483.jpeg',
            'currency': 'EUR'
        },
        {
            'id': 'web_test_3',
            'title': 'Test Item for Web UI 3',
            'query_id': 2,
            'price': 45.00,
            'timestamp': int(time.time()),
            'photo_url': 'https://images1.vinted.net/t/01_0050d_97Nn6hqaXXMZXwT5LcsFQkEx/f800/1754344834.jpeg',
            'currency': 'EUR'
        }
    ]
    
    added_count = 0
    for item in test_items:
        print(f"📝 Добавляем товар: {item['id']} - {item['title']}")
        
        result = db.add_item_to_db(
            id=item['id'],
            title=item['title'],
            query_id=item['query_id'],
            price=item['price'],
            timestamp=item['timestamp'],
            photo_url=item['photo_url'],
            currency=item['currency']
        )
        
        if result:
            print(f"✅ Товар {item['id']} добавлен успешно")
            added_count += 1
        else:
            print(f"❌ Товар {item['id']} уже существует или ошибка")
    
    print(f"📊 Добавлено товаров: {added_count}/{len(test_items)}")
    return added_count

def test_get_items_from_db():
    """Проверяем получение товаров из БД"""
    print("\n🔍 ТЕСТ ПОЛУЧЕНИЯ ТОВАРОВ ИЗ БД...")
    
    # Получаем все товары
    all_items = db.get_items(limit=100)
    print(f"📊 Всего товаров в БД: {len(all_items)}")
    
    # Получаем товары для конкретного запроса
    test_query = "https://www.vinted.de/catalog?search_text=test"
    query_items = db.get_items(limit=50, query=test_query)
    print(f"📊 Товаров для тестового запроса: {len(query_items)}")
    
    if all_items:
        print("📋 Последние 5 товаров:")
        for i, item in enumerate(all_items[:5]):
            print(f"  {i+1}. ID: {item[0]}, Title: {item[1][:50]}..., Price: {item[2]}")
    
    return len(all_items)

def test_web_ui_endpoint():
    """Тестируем эндпоинт Web UI"""
    print("\n🔍 ТЕСТ WEB UI ЭНДПОИНТА...")
    
    try:
        # Тестируем главную страницу
        response = requests.get('https://vs5-production.up.railway.app/', timeout=10)
        print(f"📡 Главная страница: {response.status_code}")
        
        # Тестируем страницу товаров
        response = requests.get('https://vs5-production.up.railway.app/items', timeout=10)
        print(f"📡 Страница товаров: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            if 'No items found' in content:
                print("❌ Web UI показывает 'No items found'")
            elif 'Test Item for Web UI' in content:
                print("✅ Web UI показывает тестовые товары")
            else:
                print("⚠️ Web UI загружается, но товары не найдены")
        else:
            print(f"❌ Ошибка загрузки Web UI: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании Web UI: {e}")

def cleanup_test_items():
    """Очищаем тестовые товары"""
    print("\n🧹 ОЧИСТКА ТЕСТОВЫХ ТОВАРОВ...")
    
    # Здесь можно добавить функцию удаления тестовых товаров
    # Пока просто выводим информацию
    print("ℹ️ Тестовые товары остаются в БД для проверки")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТА ДОБАВЛЕНИЯ ТОВАРОВ В WEB UI...")
    print("=" * 60)
    
    try:
        # Добавляем тестовые товары
        added_count = test_add_items_to_db()
        
        # Проверяем БД
        total_items = test_get_items_from_db()
        
        # Тестируем Web UI
        test_web_ui_endpoint()
        
        # Очистка
        cleanup_test_items()
        
        print("\n" + "=" * 60)
        print(f"🎉 ТЕСТ ЗАВЕРШЕН!")
        print(f"📊 Добавлено товаров: {added_count}")
        print(f"📊 Всего товаров в БД: {total_items}")
        print(f"🌐 Проверьте: https://vs5-production.up.railway.app/items")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТЕ: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")