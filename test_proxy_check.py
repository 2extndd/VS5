#!/usr/bin/env python3
"""
Тест проверки всех прокси на работоспособность
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import time
import db
from proxies import get_random_proxy, check_proxy, convert_proxy_string_to_dict
from logger import get_logger

logger = get_logger(__name__)

def test_all_proxies():
    """Проверяет все прокси из базы данных"""
    print("🔍 ТЕСТИРОВАНИЕ ВСЕХ ПРОКСИ...")
    
    # Получаем все прокси из базы
    all_proxies = []
    
    # Из параметров БД
    proxy_list_param = db.get_parameter("proxy_list")
    if proxy_list_param:
        proxy_list = eval(proxy_list_param)
        all_proxies.extend(proxy_list)
        print(f"📋 Найдено {len(proxy_list)} прокси в БД")
    
    # Из прокси ссылок  
    proxy_links_param = db.get_parameter("proxy_links")
    if proxy_links_param:
        print(f"🔗 Найдены proxy_links в БД")
    
    if not all_proxies:
        print("❌ НЕТ ПРОКСИ В БАЗЕ ДАННЫХ!")
        return [], []
        
    print(f"\n🧪 ТЕСТИРУЮ {len(all_proxies)} ПРОКСИ...\n")
    
    working_proxies = []
    failed_proxies = []
    
    for i, proxy in enumerate(all_proxies, 1):
        print(f"[{i}/{len(all_proxies)}] Тестирую: {proxy[:30]}...")
        
        start_time = time.time()
        is_working = check_proxy(proxy)
        test_time = time.time() - start_time
        
        if is_working:
            working_proxies.append(proxy)
            print(f"    ✅ РАБОТАЕТ ({test_time:.2f}s)")
        else:
            failed_proxies.append(proxy)
            print(f"    ❌ НЕ РАБОТАЕТ ({test_time:.2f}s)")
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"✅ Рабочих прокси: {len(working_proxies)}")
    print(f"❌ Нерабочих прокси: {len(failed_proxies)}")
    print(f"📈 Процент успеха: {len(working_proxies)/len(all_proxies)*100:.1f}%")
    
    if working_proxies:
        print(f"\n🎯 РАБОЧИЕ ПРОКСИ:")
        for proxy in working_proxies[:5]:  # Показываем первые 5
            print(f"  • {proxy}")
        if len(working_proxies) > 5:
            print(f"  ... и еще {len(working_proxies)-5}")
    
    return working_proxies, failed_proxies

def test_proxy_with_vinted():
    """Тестирует рабочий прокси с реальным запросом к Vinted"""
    print("\n🎯 ТЕСТИРУЮ ПРОКСИ С VINTED API...")
    
    proxy = get_random_proxy()
    if not proxy:
        print("❌ НЕТ ДОСТУПНЫХ ПРОКСИ!")
        return False
        
    print(f"🔄 Использую прокси: {proxy}")
    
    # Конвертируем прокси в dict
    proxy_dict = convert_proxy_string_to_dict(proxy)
    
    # Создаем тестовый запрос к Vinted
    test_url = "https://www.vinted.de/api/v2/catalog/items"
    test_params = {
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    try:
        print("📡 Делаю запрос к Vinted API...")
        response = requests.get(
            test_url, 
            params=test_params,
            headers=headers,
            proxies=proxy_dict,
            timeout=30,
            allow_redirects=True
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print(f"📄 Response Text (first 200 chars): {response.text[:200]}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if 'items' in json_data:
                    print(f"✅ УСПЕХ! Найдено {len(json_data['items'])} товаров")
                    return True
                else:
                    print(f"⚠️  200 OK, но нет items в ответе: {list(json_data.keys())}")
            except Exception as e:
                print(f"⚠️  200 OK, но JSON парсинг failed: {e}")
        elif response.status_code == 403:
            print("🛡️  403 Forbidden - Cloudflare блокирует")
        else:
            print(f"❌ Неуспешный запрос: {response.status_code}")
            
        return False
        
    except Exception as e:
        print(f"💥 ОШИБКА запроса: {e}")
        return False

if __name__ == "__main__":
    print("🚀 СТАРТ ТЕСТИРОВАНИЯ ПРОКСИ\n")
    
    # Инициализируем БД
    try:
        db.get_db_connection()
        print("✅ Подключение к БД успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    # Тестируем все прокси
    working_proxies, failed_proxies = test_all_proxies()
    
    # Тестируем с Vinted API
    if working_proxies:
        test_proxy_with_vinted()
    
    print("\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")