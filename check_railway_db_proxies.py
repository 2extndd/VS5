#!/usr/bin/env python3
"""
Скрипт для проверки прокси в базе данных Railway
"""

import requests
import json
import os

def check_railway_db_proxies():
    """Проверяем прокси в базе данных Railway"""
    print("🔍 Проверка прокси в базе данных Railway...")
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
            
            # Пытаемся получить данные о прокси из конфигурации
            print("\n📋 Проверьте настройки прокси в веб-интерфейсе:")
            print(f"🔗 Конфигурация: {config_url}")
            
            # Также можно попробовать получить данные через API
            print("\n💡 Для проверки прокси в базе данных Railway:")
            print("1. Откройте https://vs5-production.up.railway.app/config")
            print("2. Найдите секцию 'Proxy Settings'")
            print("3. Посмотрите настройки 'Proxy List' и 'Proxy List Link'")
            
        else:
            print(f"❌ Ошибка доступа к конфигурации: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")
    
    print("\n🔍 Альтернативные способы проверки:")
    print("1. Через веб-интерфейс: https://vs5-production.up.railway.app/config")
    print("2. Через логи Railway: railway logs | grep -i 'proxy'")
    print("3. Через переменные окружения Railway")

def check_railway_env():
    """Проверяем переменные окружения Railway"""
    print("\n🔍 Проверка переменных окружения Railway...")
    print("=" * 50)
    
    try:
        # Проверяем, есть ли доступ к Railway CLI
        import subprocess
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Railway CLI доступен")
            print("💡 Используйте команду: railway logs | grep -i 'proxy'")
        else:
            print("❌ Railway CLI недоступен")
            
    except FileNotFoundError:
        print("❌ Railway CLI не установлен")
    
    print("\n💡 Ручная проверка:")
    print("1. Откройте https://vs5-production.up.railway.app/config")
    print("2. Проверьте секцию 'Proxy Settings'")
    print("3. Посмотрите значения 'Proxy List' и 'Proxy List Link'")

if __name__ == "__main__":
    check_railway_db_proxies()
    check_railway_env() 