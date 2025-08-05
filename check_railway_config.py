#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации Railway
"""

import requests
import json

def check_railway_config():
    """Проверяем конфигурацию Railway"""
    print("🔍 Проверка конфигурации Railway...")
    print("=" * 50)
    
    # URL Railway
    base_url = "https://vs5-production.up.railway.app"
    
    try:
        # Проверяем доступность
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"✅ Railway доступен: {response.status_code}")
        
        # Проверяем конфигурацию
        config_url = f"{base_url}/config"
        response = requests.get(config_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Конфигурация доступна")
            print("\n📋 Проверьте настройки в веб-интерфейсе:")
            print(f"🔗 Конфигурация: {config_url}")
            print(f"🔗 Запросы: {base_url}/queries")
            print(f"🔗 Вещи: {base_url}/items")
            print(f"🔗 Логи: {base_url}/logs")
        else:
            print(f"❌ Ошибка доступа к конфигурации: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")
    
    print("\n💡 Рекомендации:")
    print("1. Откройте https://vs5-production.up.railway.app/config")
    print("2. Проверьте настройки прокси (Proxy Settings)")
    print("3. Увеличьте задержки между запросами")
    print("4. Проверьте логи Railway: railway logs")

if __name__ == "__main__":
    check_railway_config() 