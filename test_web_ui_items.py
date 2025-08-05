#!/usr/bin/env python3
"""
Test Web UI Items Function - найти ошибку в /items endpoint
"""

import sys
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_items_function():
    """Тест функции items() из web_ui.py"""
    print("🌐 ТЕСТ WEB UI ITEMS FUNCTION")
    print("=" * 40)
    
    try:
        import db
        print("✅ db модуль импортирован")
        
        # Test get_items function
        print("\n📋 Тестирую db.get_items()...")
        items_data = db.get_items(limit=5)
        print(f"✅ Получено {len(items_data)} items")
        
        if not items_data:
            print("⚠️  Нет items в БД")
            return True
            
        # Check item structure
        print("\n🔍 Проверяю структуру items...")
        for i, item in enumerate(items_data[:2]):
            print(f"   Item {i+1}: {len(item)} полей")
            print(f"   Структура: {[type(field).__name__ for field in item]}")
            
            # Check each field
            for j, field in enumerate(item):
                print(f"      [{j}]: {field} ({type(field).__name__})")
                
        # Test timestamp conversion
        print("\n⏰ Тестирую конвертацию timestamp...")
        test_item = items_data[0]
        
        try:
            timestamp_field = test_item[4]  # timestamp is 5th field (index 4)
            print(f"   Raw timestamp: {timestamp_field} ({type(timestamp_field).__name__})")
            
            if timestamp_field is None:
                print("   ❌ Timestamp is None!")
                return False
                
            converted = datetime.fromtimestamp(timestamp_field).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   ✅ Converted timestamp: {converted}")
            
        except Exception as e:
            print(f"   ❌ Timestamp conversion failed: {e}")
            return False
        
        # Test URL parsing  
        print("\n🔗 Тестирую парсинг URL...")
        try:
            query_url = test_item[5]  # query is 6th field (index 5)
            print(f"   Query URL: {query_url}")
            
            if query_url:
                parsed_query = urlparse(query_url)
                query_params = parse_qs(parsed_query.query)
                search_text = query_params.get('search_text', [None])[0]
                print(f"   ✅ Search text: {search_text}")
            else:
                print("   ⚠️  Query URL is None")
                
        except Exception as e:
            print(f"   ❌ URL parsing failed: {e}")
            return False
        
        # Test formatted items creation (simulate web_ui logic)
        print("\n🎨 Тестирую форматирование items...")
        try:
            formatted_items = []
            
            for item in items_data[:2]:
                formatted_item = {
                    'title': item[1],
                    'price': item[2], 
                    'currency': item[3],
                    'timestamp': datetime.fromtimestamp(item[4]).strftime('%Y-%m-%d %H:%M:%S'),
                    'query': parse_qs(urlparse(item[5]).query).get('search_text', [None])[0] if
                    parse_qs(urlparse(item[5]).query).get('search_text', [None])[0] else item[5],
                    'url': f'https://www.vinted.fr/items/{item[0]}',
                    'photo_url': item[6]
                }
                formatted_items.append(formatted_item)
                print(f"   ✅ Formatted item: {formatted_item['title']}")
                
            print(f"✅ Успешно отформатировано {len(formatted_items)} items")
            
        except Exception as e:
            print(f"   ❌ Formatting failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        # Test queries
        print("\n📝 Тестирую db.get_queries()...")
        try:
            queries = db.get_queries()
            print(f"✅ Получено {len(queries)} queries")
            
            if queries:
                for i, q in enumerate(queries[:2]):
                    print(f"   Query {i+1}: {len(q)} полей")
                    print(f"   ID: {q[0]}, URL: {q[1][:50]}...")
                    
        except Exception as e:
            print(f"   ❌ Queries test failed: {e}")
            return False
            
        print("\n🎉 ВСЕ ТЕСТЫ WEB UI ПРОШЛИ!")
        return True
        
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_items_function()
    if not success:
        sys.exit(1)