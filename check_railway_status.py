#!/usr/bin/env python3
"""
Простой скрипт для проверки статуса Railway
"""

import requests
import time

def check_railway_status():
    """Проверяем статус Railway"""
    print("🔍 Проверка статуса Railway...")
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
        
        # Проверяем страницу запросов
        queries_url = f"{base_url}/queries"
        response = requests.get(queries_url, timeout=10)
        print(f"✅ Страница запросов: {response.status_code}")
        
        # Проверяем страницу логов
        logs_url = f"{base_url}/logs"
        response = requests.get(logs_url, timeout=10)
        print(f"✅ Страница логов: {response.status_code}")
        
        print("\n💡 Проверьте вручную:")
        print(f"🔗 Главная: {base_url}/")
        print(f"🔗 Вещи: {base_url}/items")
        print(f"🔗 Запросы: {base_url}/queries")
        print(f"🔗 Конфигурация: {base_url}/config")
        print(f"🔗 Логи: {base_url}/logs")
        
        print("\n🔍 Если система не работает:")
        print("1. Проверьте логи Railway в веб-интерфейсе")
        print("2. Убедитесь, что прокси сохранились в конфигурации")
        print("3. Перезапустите приложение на Railway")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")

if __name__ == "__main__":
    check_railway_status() 