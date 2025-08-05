#!/usr/bin/env python3
"""
Детальная проверка прокси на Railway
"""

import requests
import re
import json

def check_railway_proxies_detailed():
    """Детальная проверка прокси на Railway"""
    print("🔍 Детальная проверка прокси на Railway...")
    print("=" * 50)
    
    # URL Railway
    base_url = "https://vs5-production.up.railway.app"
    
    try:
        # Получаем страницу конфигурации
        config_url = f"{base_url}/config"
        response = requests.get(config_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Конфигурация доступна")
            
            html_content = response.text
            
            # Проверяем Proxy List
            proxy_list_match = re.search(r'name="proxy_list".*?value="(.*?)"', html_content, re.DOTALL)
            if proxy_list_match:
                proxy_list_value = proxy_list_match.group(1)
                print(f"📋 Proxy List:")
                print(f"  • Длина: {len(proxy_list_value)} символов")
                if len(proxy_list_value) > 0:
                    # Подсчитываем количество прокси
                    proxy_count = len(proxy_list_value.split('\n'))
                    print(f"  • Количество строк: {proxy_count}")
                    print(f"  • Начало: {proxy_list_value[:100]}...")
                    
                    # Проверяем формат прокси
                    first_proxy = proxy_list_value.split('\n')[0] if proxy_list_value else ""
                    if '@' in first_proxy and ':' in first_proxy:
                        print(f"  • Формат прокси: ✅ Правильный")
                    else:
                        print(f"  • Формат прокси: ❌ Неправильный")
                else:
                    print(f"  • Статус: ❌ Пустой")
            else:
                print(f"  • Статус: ❌ Не найден")
            
            # Проверяем Check Proxies
            check_proxies_match = re.search(r'name="check_proxies".*?checked', html_content, re.DOTALL)
            if check_proxies_match:
                print(f"📋 Check Proxies: ✅ Включен")
            else:
                print(f"📋 Check Proxies: ❌ Выключен")
            
            # Проверяем Proxy List Link
            proxy_link_match = re.search(r'name="proxy_list_link".*?value="(.*?)"', html_content, re.DOTALL)
            if proxy_link_match:
                proxy_link_value = proxy_link_match.group(1)
                if proxy_link_value:
                    print(f"📋 Proxy List Link: ✅ {proxy_link_value}")
                else:
                    print(f"📋 Proxy List Link: ❌ Пустой")
            else:
                print(f"📋 Proxy List Link: ❌ Не найден")
                
        else:
            print(f"❌ Ошибка доступа к конфигурации: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка подключения к Railway: {e}")
    
    print("\n💡 Рекомендации:")
    print("1. Если Proxy List пустой - добавьте прокси")
    print("2. Если Check Proxies выключен - включите его")
    print("3. Если прокси есть, но система не работает - перезапустите приложение")
    
    print("\n🔍 Проверка логов:")
    print("1. Откройте https://vs5-production.up.railway.app/logs")
    print("2. Ищите записи с 'proxy', '403', 'forbidden'")
    print("3. Проверьте, есть ли записи 'Using proxy' или 'get_random_proxy'")

def check_railway_logs():
    """Проверяем логи Railway"""
    print("\n🔍 Проверка логов Railway...")
    print("=" * 50)
    
    try:
        # Получаем страницу логов
        logs_url = "https://vs5-production.up.railway.app/logs"
        response = requests.get(logs_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Логи доступны")
            
            # Ищем записи о прокси
            html_content = response.text
            
            # Ищем последние записи
            log_entries = re.findall(r'<div class="log-entry">(.*?)</div>', html_content, re.DOTALL)
            
            if log_entries:
                print(f"📋 Найдено {len(log_entries)} записей в логах")
                
                # Ищем записи о прокси
                proxy_entries = [entry for entry in log_entries if 'proxy' in entry.lower()]
                if proxy_entries:
                    print(f"📋 Найдено {len(proxy_entries)} записей о прокси")
                    for entry in proxy_entries[-3:]:  # Последние 3
                        print(f"  • {entry[:100]}...")
                else:
                    print("❌ Записей о прокси не найдено")
                
                # Ищем записи о 403 ошибках
                error_entries = [entry for entry in log_entries if '403' in entry or 'forbidden' in entry.lower()]
                if error_entries:
                    print(f"📋 Найдено {len(error_entries)} записей об ошибках 403")
                    for entry in error_entries[-3:]:  # Последние 3
                        print(f"  • {entry[:100]}...")
                else:
                    print("✅ Записей об ошибках 403 не найдено")
            else:
                print("❌ Записи в логах не найдены")
        else:
            print(f"❌ Ошибка доступа к логам: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка получения логов: {e}")

if __name__ == "__main__":
    check_railway_proxies_detailed()
    check_railway_logs() 