#!/usr/bin/env python3
"""
Тест исправлений прокси
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pyVintedVN.vinted import Vinted
from logger import get_logger

logger = get_logger(__name__)

def test_vinted_with_proxy():
    """Тестируем Vinted с прокси"""
    print("🔍 Тестирование Vinted с исправлениями прокси...")
    print("=" * 50)
    
    try:
        # Создаем Vinted экземпляр
        vinted = Vinted()
        
        # Тестовый URL
        test_url = "https://www.vinted.de/catalog?search_text=&catalog_ids=19&brand_ids=212366&currency=EUR&price_to=50&page=1&per_page=2&order=newest_first"
        
        print(f"🔗 Тестируем URL: {test_url}")
        
        # Выполняем поиск
        items = vinted.items.search(test_url, nbr_items=2)
        
        print(f"✅ Поиск успешен!")
        print(f"📦 Найдено вещей: {len(items)}")
        
        if items:
            print(f"📋 Первая вещь:")
            item = items[0]
            print(f"  • ID: {item.id}")
            print(f"  • Title: {item.title}")
            print(f"  • Price: {item.price}")
            print(f"  • Brand: {item.brand}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_vinted_with_proxy()
    if success:
        print("\n✅ Исправления прокси работают!")
    else:
        print("\n❌ Исправления требуют доработки!")