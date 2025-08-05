#!/usr/bin/env python3
"""
Тест получения токена авторизации для Vinted API
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import re
import json
from pyVintedVN.requester import requester as requester_class
from proxies import get_random_proxy, convert_proxy_string_to_dict
from logger import get_logger

logger = get_logger(__name__)

def get_vinted_csrf_token():
    """Получает CSRF токен с главной страницы Vinted"""
    print("🔑 ПОЛУЧЕНИЕ CSRF ТОКЕНА...")
    
    proxy = get_random_proxy()
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        if proxy:
            proxy_dict = convert_proxy_string_to_dict(proxy)
            session.proxies.update(proxy_dict)
            print(f"🔄 Используем прокси: {proxy}")
        
        # Запросы к главной странице для получения cookies и токенов
        print("📡 Запрос к https://www.vinted.de/")
        response = session.get("https://www.vinted.de/", timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        
        # Обработка дублирующихся cookies
        try:
            cookies_dict = {}
            for cookie in session.cookies:
                cookies_dict[cookie.name] = cookie.value
            print(f"🍪 Cookies: {cookies_dict}")
        except Exception as e:
            print(f"⚠️  Cookie error: {e}")
            print(f"🍪 Raw Cookies: {session.cookies}")
        
        if response.status_code == 200:
            # Ищем CSRF токен в HTML
            csrf_patterns = [
                r'name="csrf-token"\s+content="([^"]+)"',
                r'"csrf_token"\s*:\s*"([^"]+)"',
                r'window\.CSRF_TOKEN\s*=\s*["\']([^"\']+)["\']',
                r'csrf_token["\']?\s*:\s*["\']([^"\']+)["\']'
            ]
            
            # Получаем access_token_web из cookies (Bearer токен)
            access_token = None
            for cookie in session.cookies:
                if cookie.name == 'access_token_web':
                    access_token = cookie.value
                    print(f"✅ Access Token найден: {access_token[:50]}...")
                    break
            
            if not access_token:
                print("❌ Access Token не найден в cookies")
                # Также пробуем найти CSRF токен в HTML как fallback
                csrf_token = None
                for pattern in csrf_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        csrf_token = match.group(1)
                        print(f"⚠️  Fallback CSRF Token найден: {csrf_token[:20]}...")
                        access_token = csrf_token
                        break
                
                if not access_token:
                    print(f"📄 HTML содержимое (первые 1000 символов):\n{response.text[:1000]}")
            
            return access_token, session
        else:
            print(f"❌ Ошибка получения главной страницы: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return None, None

def test_vinted_api_with_token():
    """Тестирует API запрос с полученным токеном"""
    print("\n🎯 ТЕСТ API С ТОКЕНОМ...")
    
    access_token, session = get_vinted_csrf_token()
    
    if not access_token or not session:
        print("❌ Не удалось получить токен")
        return False
    
    # Обновляем headers для API запроса
    api_headers = {
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
        "Authorization": f"Bearer {access_token}",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    session.headers.update(api_headers)
    
    # API запрос
    api_url = "https://www.vinted.de/api/v2/catalog/items"
    params = {
        'catalog_ids': '19',
        'price_to': '50.0',
        'currency': 'EUR', 
        'brand_ids': '212366',
        'order': 'newest_first',
        'per_page': 5,
        'page': 1
    }
    
    try:
        print("📡 API запрос с токеном...")
        response = session.get(api_url, params=params, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        print(f"📄 Response (первые 300 символов): {response.text[:300]}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if 'items' in json_data:
                    print(f"✅ УСПЕХ! Найдено {len(json_data['items'])} товаров с токеном!")
                    for i, item in enumerate(json_data['items'][:3]):
                        print(f"  {i+1}. {item.get('title', 'No title')} - {item.get('price', 'No price')}")
                    return True
                else:
                    print(f"⚠️  200 OK, но нет items: {list(json_data.keys())}")
            except:
                print(f"❌ JSON parsing error")
        else:
            print(f"❌ API запрос неуспешен: {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"💥 Ошибка API запроса: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ТЕСТ АВТОРИЗАЦИИ VINTED\n")
    
    # Инициализируем БД
    import db
    try:
        db.get_db_connection()
        print("✅ Подключение к БД успешно\n")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    # Тестируем авторизацию
    success = test_vinted_api_with_token()
    
    if success:
        print("\n🎉 АВТОРИЗАЦИЯ РАБОТАЕТ!")
    else:
        print("\n❌ АВТОРИЗАЦИЯ НЕ РАБОТАЕТ")
    
    print("\n🏁 ТЕСТ ЗАВЕРШЕН")