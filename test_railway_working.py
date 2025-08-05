#!/usr/bin/env python3
"""
Проверка работы системы с прокси на Railway
"""

import requests
import time

def test_railway_working():
    """Проверяем работу системы с прокси"""
    print("🔍 Проверка работы системы с прокси на Railway...")
    print("=" * 50)
    
    # URL Railway
    base_url = "https://vs5-production.up.railway.app"
    
    try:
        # Проверяем главную страницу
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"✅ Главная страница: {response.status_code}")
        
        # Проверяем страницу вещей
        items_url = f"{base_url}/items"
        response = requests.get(items_url, timeout=10)
        print(f"✅ Страница вещей: {response.status_code}")
        
        # Проверяем количество вещей
        if response.status_code == 200:
            html_content = response.text
            # Ищем количество вещей
            import re
            items_count_match = re.search(r'Total Items: (\d+)', html_content)
            if items_count_match:
                items_count = items_count_match.group(1)
                print(f"📦 Всего вещей в базе: {items_count}")
            else:
                print("📦 Количество вещей не найдено")
        
        # Проверяем страницу запросов
        queries_url = f"{base_url}/queries"
        response = requests.get(queries_url, timeout=10)
        print(f"✅ Страница запросов: {response.status_code}")
        
        # Проверяем количество запросов
        if response.status_code == 200:
            html_content = response.text
            # Ищем количество запросов
            queries_count_match = re.search(r'Found (\d+) queries', html_content)
            if queries_count_match:
                queries_count = queries_count_match.group(1)
                print(f"🔍 Количество запросов: {queries_count}")
            else:
                print("🔍 Количество запросов не найдено")
        
        print("\n💡 Проверьте вручную:")
        print(f"🔗 Вещи: {base_url}/items")
        print(f"🔗 Запросы: {base_url}/queries")
        print(f"🔗 Логи: {base_url}/logs")
        
        print("\n🔍 Что искать в логах:")
        print("1. Записи 'get_random_proxy' - система получает прокси")
        print("2. Записи 'Using proxy' - система использует прокси")
        print("3. Записи 'Found X items' - система находит вещи")
        print("4. Записи '403' или 'forbidden' - ошибки блокировки")
        
        print("\n⏰ Подождите 2-3 минуты и проверьте логи снова")
        print("Система должна начать работать с прокси")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")

if __name__ == "__main__":
    test_railway_working() 