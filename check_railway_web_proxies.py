#!/usr/bin/env python3
"""
Скрипт для проверки прокси через веб-интерфейс Railway
"""

import requests
import json
import re

def check_railway_web_proxies():
    """Проверяем прокси через веб-интерфейс Railway"""
    print("🔍 Проверка прокси через веб-интерфейс Railway...")
    print("=" * 50)
    
    # URL Railway
    base_url = "https://vs5-production.up.railway.app"
    
    try:
        # Получаем страницу конфигурации
        config_url = f"{base_url}/config"
        response = requests.get(config_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Конфигурация доступна")
            
            # Ищем информацию о прокси в HTML
            html_content = response.text
            
            # Ищем секцию с прокси
            proxy_section = re.search(r'Proxy Settings.*?</form>', html_content, re.DOTALL | re.IGNORECASE)
            
            if proxy_section:
                print("📋 Найдена секция Proxy Settings")
                
                # Ищем proxy_list
                proxy_list_match = re.search(r'name="proxy_list".*?value="(.*?)"', proxy_section.group(), re.DOTALL)
                if proxy_list_match:
                    proxy_list_value = proxy_list_match.group(1)
                    print(f"📋 Proxy List найден (длина: {len(proxy_list_value)} символов)")
                    if len(proxy_list_value) > 0:
                        print(f"📋 Начало: {proxy_list_value[:100]}...")
                    else:
                        print("❌ Proxy List пустой")
                else:
                    print("❌ Proxy List не найден")
                
                # Ищем proxy_list_link
                proxy_link_match = re.search(r'name="proxy_list_link".*?value="(.*?)"', proxy_section.group(), re.DOTALL)
                if proxy_link_match:
                    proxy_link_value = proxy_link_match.group(1)
                    print(f"📋 Proxy List Link: {proxy_link_value}")
                else:
                    print("❌ Proxy List Link не найден")
                    
            else:
                print("❌ Секция Proxy Settings не найдена")
                
        else:
            print(f"❌ Ошибка доступа к конфигурации: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")
    
    print("\n💡 Ручная проверка:")
    print("1. Откройте https://vs5-production.up.railway.app/config")
    print("2. Найдите секцию 'Proxy Settings'")
    print("3. Посмотрите значения полей:")
    print("   - Proxy List")
    print("   - Proxy List Link")
    print("   - Check Proxies (должно быть включено)")
    
    print("\n🔍 Если прокси не настроены:")
    print("1. Добавьте все 50 прокси в поле 'Proxy List'")
    print("2. Или добавьте ссылку в 'Proxy List Link':")
    print("   https://sx-list.org/jXqrKIfIr2A87CEAsnKeHJ3OIroEhO5n.txt?limit=50&type=res&use_login_and_password=1&country=DE")
    print("3. Включите 'Check Proxies'")
    print("4. Нажмите 'Save Configuration'")

if __name__ == "__main__":
    check_railway_web_proxies() 