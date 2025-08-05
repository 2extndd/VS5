#!/usr/bin/env python3
"""
Тест прямого обращения к Vinted API для диагностики
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import db
from pyVintedVN.requester import requester
from pyVintedVN.items.items import Items
from logger import get_logger

logger = get_logger(__name__)

def test_direct_vinted_request():
    """Прямой запрос к Vinted API без библиотеки"""
    print("🔍 ТЕСТ ПРЯМОГО ЗАПРОСА К VINTED API...")
    
    url = "https://www.vinted.de/api/v2/catalog/items"
    params = {
        'catalog_ids': '19',
        'price_to': '50.0', 
        'currency': 'EUR',
        'brand_ids': '212366',
        'order': 'newest_first',
        'per_page': 5,
        'page': 1
    }
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd", 
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty", 
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.vinted.de/",
        "Origin": "https://www.vinted.de",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    print(f"📡 URL: {url}")
    print(f"📋 Params: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        print(f"\n📊 РЕЗУЛЬТАТ:")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Response Length: {len(response.text)}")
        print(f"Response Text (first 500 chars):\n{response.text[:500]}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if 'items' in json_data:
                    print(f"\n✅ УСПЕХ! Найдено {len(json_data['items'])} товаров")
                    for i, item in enumerate(json_data['items'][:3]):
                        print(f"  {i+1}. {item.get('title', 'No title')} - {item.get('price', 'No price')}")
                    return True
                else:
                    print(f"\n⚠️  200 OK, но нет 'items' в ответе")
                    print(f"Ключи ответа: {list(json_data.keys())}")
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON парсинг failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"\n💥 ОШИБКА запроса: {e}")
        return False

def test_requester_class():
    """Тест класса requester"""
    print("\n🔧 ТЕСТ КЛАССА REQUESTER...")
    
    try:
        # Создаем экземпляр requester
        from pyVintedVN.requester import requester as requester_class
        req = requester_class(debug=True)
        print("✅ Requester создан успешно")
        
        # Тестируем метод get
        url = "https://www.vinted.de/api/v2/catalog/items"
        params = {
            'catalog_ids': '19',
            'price_to': '50.0',
            'currency': 'EUR', 
            'brand_ids': '212366',
            'order': 'newest_first',
            'per_page': 5,
            'page': 1
        }
        
        print(f"📡 Делаю запрос через requester...")
        response = req.get(url, params=params)
        
        print(f"📊 Status: {response.status_code}")
        print(f"📄 Response Length: {len(response.text)}")
        print(f"📄 Response Text (first 300 chars): {response.text[:300]}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if 'items' in json_data:
                    print(f"✅ REQUESTER РАБОТАЕТ! Найдено {len(json_data['items'])} товаров")
                    return True
                else:
                    print(f"⚠️  200 OK через requester, но нет items")
            except:
                print(f"❌ JSON парсинг через requester failed")
        
        return False
        
    except Exception as e:
        print(f"💥 ОШИБКА в requester: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_items_class():
    """Тест класса Items из pyVintedVN"""
    print("\n📦 ТЕСТ КЛАССА ITEMS...")
    
    try:
        # Создаем экземпляр Items
        items = Items()
        print("✅ Items класс создан успешно")
        
        # Тестируем поиск
        test_url = "https://www.vinted.de/catalog?catalog%5B%5D=19&price_to=50.0&currency=EUR&brand_ids%5B%5D=212366&order=newest_first"
        
        print(f"🔍 Поиск по URL: {test_url}")
        results = items.search(test_url)
        
        print(f"📊 Результатов: {len(results) if results else 0}")
        
        if results and len(results) > 0:
            print(f"✅ ITEMS.SEARCH РАБОТАЕТ! Найдено {len(results)} товаров")
            for i, item in enumerate(results[:3]):
                print(f"  {i+1}. {item.title} - {item.price} {item.currency}")
            return True
        else:
            print(f"❌ Items.search вернул пустой результат")
        
        return False
        
    except Exception as e:
        print(f"💥 ОШИБКА в Items: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_queries():
    """Тест запросов из базы данных"""
    print("\n🗄️  ТЕСТ ЗАПРОСОВ ИЗ БД...")
    
    try:
        queries = db.get_queries()
        print(f"📋 Найдено {len(queries)} запросов в БД:")
        
        for i, query in enumerate(queries):
            print(f"  {i+1}. ID:{query[0]} - {query[1][:60]}...")
            
        return queries
        
    except Exception as e:
        print(f"💥 ОШИБКА получения запросов: {e}")
        return []

if __name__ == "__main__":
    print("🚀 СТАРТ ДИАГНОСТИКИ VINTED API\n")
    
    # Инициализируем БД
    try:
        db.get_db_connection()
        print("✅ Подключение к БД успешно\n")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    # Запускаем тесты
    results = {}
    
    results['direct'] = test_direct_vinted_request()
    results['requester'] = test_requester_class()  
    results['items'] = test_items_class()
    
    # Проверяем БД
    queries = test_database_queries()
    
    print(f"\n📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print(f"🔍 Прямой запрос: {'✅' if results['direct'] else '❌'}")
    print(f"🔧 Requester класс: {'✅' if results['requester'] else '❌'}")
    print(f"📦 Items класс: {'✅' if results['items'] else '❌'}")
    print(f"🗄️  Запросы в БД: {len(queries)}")
    
    if not any(results.values()):
        print(f"\n🚨 ВСЕ ТЕСТЫ ПРОВАЛИЛИСЬ - VINTED API НЕДОСТУПЕН!")
    else:
        print(f"\n🎯 НЕКОТОРЫЕ ТЕСТЫ ПРОШЛИ - ПРОБЛЕМА В КОНКРЕТНОМ КОМПОНЕНТЕ")
    
    print("\n🏁 ДИАГНОСТИКА ЗАВЕРШЕНА")