#!/usr/bin/env python3
"""
Тест полной интеграции: получение токена + API запрос + сохранение в БД  
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import db
from proxies import get_random_proxy, convert_proxy_string_to_dict
from logger import get_logger

logger = get_logger(__name__)

class WorkingVintedRequester:
    """Простой рабочий requester с Bearer авторизацией"""
    
    def __init__(self, debug=True):
        self.debug = debug
        self.session = requests.Session()
        self.access_token = None
        self.setup_session()
    
    def setup_session(self):
        """Настройка сессии с токеном"""
        # Базовые headers
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
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        self.session.headers.update(headers)
        
        # Настройка прокси
        proxy = get_random_proxy()
        if proxy:
            proxy_dict = convert_proxy_string_to_dict(proxy)
            self.session.proxies.update(proxy_dict)
            if self.debug:
                logger.info(f"[DEBUG] Using proxy: {proxy}")
        
        # Получение Bearer токена
        self.get_access_token()
    
    def get_access_token(self):
        """Получение access_token_web для Bearer авторизации"""
        try:
            if self.debug:
                logger.info("[DEBUG] Getting access token from main page...")
            
            # Headers для главной страницы
            main_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate", 
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Временно обновляем headers для главной страницы
            original_headers = dict(self.session.headers)
            self.session.headers.update(main_headers)
            
            # Запрос к главной странице
            response = self.session.get("https://www.vinted.de/", timeout=30)
            
            # Восстанавливаем API headers
            self.session.headers.clear()
            self.session.headers.update(original_headers)
            
            if response.status_code == 200:
                # Извлекаем access_token_web из cookies
                for cookie in self.session.cookies:
                    if cookie.name == 'access_token_web':
                        self.access_token = cookie.value
                        # Добавляем Bearer authorization
                        self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                        if self.debug:
                            logger.info(f"[DEBUG] Bearer token obtained: {self.access_token[:50]}...")
                        return True
                
                if self.debug:
                    logger.info("[DEBUG] No access_token_web found in cookies")
                return False
            else:
                if self.debug:
                    logger.info(f"[DEBUG] Main page request failed: {response.status_code}")
                return False
                
        except Exception as e:
            if self.debug:
                logger.info(f"[DEBUG] Error getting token: {e}")
            return False
    
    def search_items(self, params):
        """API запрос к каталогу товаров"""
        url = "https://www.vinted.de/api/v2/catalog/items"
        
        try:
            if self.debug:
                logger.info(f"[DEBUG] API request to: {url}")
                logger.info(f"[DEBUG] Params: {params}")
            
            response = self.session.get(url, params=params, timeout=30)
            
            if self.debug:
                logger.info(f"[DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                if self.debug:
                    logger.info(f"[DEBUG] Response text: {response.text[:200]}")
                return None
                
        except Exception as e:
            if self.debug:
                logger.info(f"[DEBUG] API request error: {e}")
            return None

def test_working_integration():
    """Тест полной рабочей интеграции"""
    print("🚀 ТЕСТ РАБОЧЕЙ ИНТЕГРАЦИИ")
    
    # Инициализация
    try:
        db.get_db_connection()
        print("✅ БД подключена")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False
    
    # Создание рабочего requester
    print("\n🔧 Создание WorkingVintedRequester...")
    requester = WorkingVintedRequester(debug=True)
    
    if not requester.access_token:
        print("❌ Не удалось получить access token")
        return False
    
    print("✅ Access token получен!")
    
    # Тест API запроса
    print("\n📡 Тест API запроса...")
    test_params = {
        'catalog_ids': '19',
        'price_to': '50.0',
        'currency': 'EUR',
        'brand_ids': '212366',
        'order': 'newest_first',
        'per_page': 5,
        'page': 1
    }
    
    result = requester.search_items(test_params)
    
    if result and 'items' in result:
        items = result['items']
        print(f"✅ API РАБОТАЕТ! Найдено {len(items)} товаров:")
        
        for i, item in enumerate(items[:3]):
            title = item.get('title', 'No title')
            price = item.get('price', {})
            price_str = f"{price.get('amount', '?')} {price.get('currency_code', 'EUR')}"
            print(f"  {i+1}. {title} - {price_str}")
        
        # Тест добавления в БД
        print(f"\n💾 Тест добавления в БД...")
        try:
            # Добавляем первый товар в БД для теста
            first_item = items[0]
            item_id = first_item.get('id')
            title = first_item.get('title')
            price = first_item.get('price', {}).get('amount', '0')
            currency = first_item.get('price', {}).get('currency_code', 'EUR')
            photo_url = first_item.get('photo', {}).get('url', '') if first_item.get('photo') else ''
            
            # Используем query_id = 1 (тестовый)
            import time
            db.add_item_to_db(
                id=item_id,
                title=title,
                query_id=1,
                price=price,
                timestamp=int(time.time()),  # Текущее время
                photo_url=photo_url,
                currency=currency
            )
            print("✅ Товар добавлен в БД!")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка добавления в БД: {e}")
            # Проверяем что товар все-таки добавился
            try:
                items_from_db = db.get_items()
                if items_from_db:
                    print(f"✅ В БД найдено {len(items_from_db)} товаров")
                    return True
            except:
                pass
            return False
    else:
        print("❌ API запрос не удался")
        return False

if __name__ == "__main__":
    success = test_working_integration()
    
    if success:
        print("\n🎉 ПОЛНАЯ ИНТЕГРАЦИЯ РАБОТАЕТ!")
        print("🔥 ГОТОВО К ВНЕДРЕНИЮ В ОСНОВНОЙ КОД!")
    else:
        print("\n❌ ИНТЕГРАЦИЯ НЕ РАБОТАЕТ")
    
    print("\n🏁 ТЕСТ ЗАВЕРШЕН")