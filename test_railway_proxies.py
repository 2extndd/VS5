#!/usr/bin/env python3
"""
Скрипт для проверки прокси на Railway
"""

import os
import sys
import requests
import time
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
import proxies
from logger import get_logger

logger = get_logger(__name__)

def check_railway_proxies():
    """Проверяем прокси на Railway"""
    print("🔍 Проверка прокси на Railway...")
    print("=" * 50)
    
    # Проверяем подключение к базе данных
    try:
        conn, db_type = db.get_db_connection()
        print(f"✅ Подключение к БД: {db_type}")
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return
    
    # Проверяем настройки прокси в БД
    print("\n📋 Настройки прокси в базе данных:")
    
    proxy_list = db.get_parameter("proxy_list")
    if proxy_list:
        print(f"✅ proxy_list: {proxy_list[:100]}...")
    else:
        print("❌ proxy_list не настроен")
    
    proxy_list_link = db.get_parameter("proxy_list_link")
    if proxy_list_link:
        print(f"✅ proxy_list_link: {proxy_list_link}")
    else:
        print("❌ proxy_list_link не настроен")
    
    # Проверяем, работает ли get_random_proxy
    print("\n🔄 Тестирование get_random_proxy():")
    try:
        proxy = proxies.get_random_proxy()
        if proxy:
            print(f"✅ Получен прокси: {proxy[:50]}...")
            
            # Тестируем прокси с Vinted
            print("\n🌐 Тестирование прокси с Vinted:")
            proxy_dict = proxies.convert_proxy_string_to_dict(proxy)
            
            session = requests.Session()
            session.proxies.update(proxy_dict)
            
            # Добавляем заголовки
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive"
            })
            
            # Тестируем с Vinted
            test_url = "https://www.vinted.de/api/v2/catalog/items?search_text=&catalog_ids=19&brand_ids=212366&currency=EUR&price_to=50&page=1&per_page=2&order=newest_first"
            
            print(f"🔗 Тестируем URL: {test_url}")
            
            response = session.get(test_url, timeout=10)
            print(f"📊 Статус: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Прокси работает с Vinted!")
                data = response.json()
                print(f"📦 Найдено товаров: {len(data.get('items', []))}")
            elif response.status_code == 403:
                print("❌ Vinted заблокировал запрос (403 Forbidden)")
                print("💡 Возможные причины:")
                print("   - Vinted заблокировал IP прокси")
                print("   - Слишком частые запросы")
                print("   - Неправильные заголовки")
            else:
                print(f"⚠️ Неожиданный статус: {response.status_code}")
                
        else:
            print("❌ get_random_proxy() вернул None")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании прокси: {e}")
    
    # Проверяем логи Railway
    print("\n📋 Последние логи Railway:")
    print("💡 Используйте команду: railway logs | grep -i 'proxy\\|403\\|forbidden' | tail -10")

if __name__ == "__main__":
    check_railway_proxies() 