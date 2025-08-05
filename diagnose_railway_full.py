#!/usr/bin/env python3
"""
Полная диагностика системы на Railway
"""

import requests
import re
import time
import json
from datetime import datetime

def test_proxy_link():
    """Тестируем ссылку на прокси"""
    print("🔍 Тестирование ссылки на прокси...")
    print("=" * 50)
    
    proxy_url = "https://sx-list.org/jXqrKIfIr2A87CEAsnKeHJ3OIroEhO5n.txt?limit=100&type=res&use_login_and_password=1&country=DE"
    
    try:
        response = requests.get(proxy_url, timeout=10)
        if response.status_code == 200:
            proxies_text = response.text.strip()
            proxies_list = [p.strip() for p in proxies_text.split() if p.strip()]
            
            print(f"✅ Ссылка работает: {response.status_code}")
            print(f"📦 Найдено прокси: {len(proxies_list)}")
            print(f"📋 Первые 3 прокси:")
            for i, proxy in enumerate(proxies_list[:3], 1):
                print(f"  {i}. {proxy}")
            
            # Проверяем формат прокси
            if proxies_list and '@' in proxies_list[0] and ':' in proxies_list[0]:
                print(f"✅ Формат прокси правильный")
            else:
                print(f"❌ Неправильный формат прокси")
                
            return len(proxies_list) > 0
        else:
            print(f"❌ Ошибка загрузки прокси: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования ссылки: {e}")
        return False

def check_railway_proxy_config():
    """Проверяем конфигурацию прокси на Railway"""
    print("\n🔍 Проверка конфигурации прокси на Railway...")
    print("=" * 50)
    
    try:
        config_url = "https://vs5-production.up.railway.app/config"
        response = requests.get(config_url, timeout=10)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Проверяем Proxy List
            proxy_list_match = re.search(r'name="proxy_list"[^>]*value="([^"]*)"', html_content)
            proxy_list_value = proxy_list_match.group(1) if proxy_list_match else ""
            
            print(f"📋 Proxy List:")
            if len(proxy_list_value) > 0:
                print(f"  • Статус: ❌ Не пустой ({len(proxy_list_value)} символов)")
                print(f"  • Содержимое: {proxy_list_value[:100]}...")
            else:
                print(f"  • Статус: ✅ Пустой (правильно)")
            
            # Проверяем Proxy List Link
            proxy_link_match = re.search(r'name="proxy_list_link"[^>]*value="([^"]*)"', html_content)
            proxy_link_value = proxy_link_match.group(1) if proxy_link_match else ""
            
            print(f"📋 Proxy List Link:")
            if proxy_link_value:
                print(f"  • Статус: ✅ Настроен")
                print(f"  • URL: {proxy_link_value}")
            else:
                print(f"  • Статус: ❌ Не настроен")
            
            # Проверяем Check Proxies
            check_proxies_enabled = 'name="check_proxies"' in html_content and 'checked' in html_content
            print(f"📋 Check Proxies: {'✅ Включен' if check_proxies_enabled else '❌ Выключен'}")
            
            return proxy_link_value != "" and len(proxy_list_value) == 0
            
        else:
            print(f"❌ Ошибка доступа к конфигурации: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")
        return False

def check_railway_logs():
    """Анализируем логи Railway"""
    print("\n🔍 Анализ логов Railway...")
    print("=" * 50)
    
    try:
        logs_url = "https://vs5-production.up.railway.app/logs"
        response = requests.get(logs_url, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Ищем записи в логах
            log_pattern = r'<div[^>]*class="[^"]*log[^"]*"[^>]*>(.*?)</div>'
            log_entries = re.findall(log_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if not log_entries:
                # Альтернативный поиск
                log_pattern = r'<pre[^>]*>(.*?)</pre>'
                log_entries = re.findall(log_pattern, html_content, re.DOTALL)
            
            print(f"📋 Найдено записей в логах: {len(log_entries)}")
            
            if log_entries:
                # Анализируем последние записи
                recent_logs = log_entries[-20:] if len(log_entries) > 20 else log_entries
                
                # Ищем ключевые события
                proxy_mentions = 0
                error_403_count = 0
                process_items_calls = 0
                scheduler_events = 0
                
                for log in recent_logs:
                    log_text = log.lower()
                    if 'proxy' in log_text:
                        proxy_mentions += 1
                    if '403' in log_text or 'forbidden' in log_text:
                        error_403_count += 1
                    if 'process_items' in log_text:
                        process_items_calls += 1
                    if 'scheduler' in log_text:
                        scheduler_events += 1
                
                print(f"📊 Анализ логов:")
                print(f"  • Упоминания прокси: {proxy_mentions}")
                print(f"  • Ошибки 403: {error_403_count}")
                print(f"  • Вызовы process_items: {process_items_calls}")
                print(f"  • События планировщика: {scheduler_events}")
                
                # Показываем последние записи
                print(f"\n📋 Последние 5 записей:")
                for i, log in enumerate(recent_logs[-5:], 1):
                    clean_log = re.sub(r'<[^>]+>', '', log).strip()[:100]
                    print(f"  {i}. {clean_log}...")
                
                return {
                    'proxy_mentions': proxy_mentions,
                    'error_403_count': error_403_count,
                    'process_items_calls': process_items_calls,
                    'scheduler_events': scheduler_events
                }
            else:
                print("❌ Записи в логах не найдены")
                return None
                
        else:
            print(f"❌ Ошибка доступа к логам: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка анализа логов: {e}")
        return None

def check_railway_queries():
    """Проверяем запросы на Railway"""
    print("\n🔍 Проверка запросов на Railway...")
    print("=" * 50)
    
    try:
        queries_url = "https://vs5-production.up.railway.app/queries"
        response = requests.get(queries_url, timeout=10)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Ищем количество запросов
            queries_match = re.search(r'Found (\d+) queries|(\d+) queries found', html_content, re.IGNORECASE)
            if queries_match:
                queries_count = queries_match.group(1) or queries_match.group(2)
                print(f"📋 Количество запросов: {queries_count}")
            else:
                print("📋 Количество запросов не найдено")
            
            # Ищем записи о последних найденных вещах
            last_found_pattern = r'Last Found Item.*?(\d{4}-\d{2}-\d{2}|\w+)'
            last_found_matches = re.findall(last_found_pattern, html_content, re.IGNORECASE)
            
            if last_found_matches:
                print(f"📋 Последние найденные вещи:")
                for i, match in enumerate(last_found_matches[:3], 1):
                    print(f"  {i}. {match}")
            else:
                print("📋 Информация о последних найденных вещах не найдена")
            
            return True
            
        else:
            print(f"❌ Ошибка доступа к запросам: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки запросов: {e}")
        return False

def check_railway_items():
    """Проверяем вещи на Railway"""
    print("\n🔍 Проверка вещей на Railway...")
    print("=" * 50)
    
    try:
        items_url = "https://vs5-production.up.railway.app/items"
        response = requests.get(items_url, timeout=10)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Ищем общее количество вещей
            total_match = re.search(r'Total Items?\s*:?\s*(\d+)', html_content, re.IGNORECASE)
            if total_match:
                total_items = total_match.group(1)
                print(f"📦 Общее количество вещей: {total_items}")
            else:
                print("📦 Общее количество вещей не найдено")
            
            # Ищем последние добавленные вещи
            recent_items_pattern = r'(\d{4}-\d{2}-\d{2})'
            recent_dates = re.findall(recent_items_pattern, html_content)
            
            if recent_dates:
                unique_dates = list(set(recent_dates))[-3:]
                print(f"📋 Последние даты добавления вещей:")
                for date in sorted(unique_dates, reverse=True):
                    print(f"  • {date}")
            else:
                print("📋 Даты добавления вещей не найдены")
            
            return True
            
        else:
            print(f"❌ Ошибка доступа к вещам: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки вещей: {e}")
        return False

def main():
    """Основная функция диагностики"""
    print("🚀 ПОЛНАЯ ДИАГНОСТИКА RAILWAY СИСТЕМЫ")
    print("=" * 60)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Тестируем ссылку на прокси
    proxy_link_ok = test_proxy_link()
    
    # 2. Проверяем конфигурацию
    config_ok = check_railway_proxy_config()
    
    # 3. Анализируем логи
    logs_analysis = check_railway_logs()
    
    # 4. Проверяем запросы
    queries_ok = check_railway_queries()
    
    # 5. Проверяем вещи
    items_ok = check_railway_items()
    
    # Выводим результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ")
    print("=" * 60)
    
    print(f"✅ Ссылка на прокси: {'OK' if proxy_link_ok else 'FAIL'}")
    print(f"✅ Конфигурация прокси: {'OK' if config_ok else 'FAIL'}")
    print(f"✅ Запросы: {'OK' if queries_ok else 'FAIL'}")
    print(f"✅ Вещи: {'OK' if items_ok else 'FAIL'}")
    
    if logs_analysis:
        print(f"📊 Активность системы:")
        print(f"  • Планировщик: {'OK' if logs_analysis['scheduler_events'] > 0 else 'FAIL'}")
        print(f"  • Прокси: {'OK' if logs_analysis['proxy_mentions'] > 0 else 'FAIL'}")
        print(f"  • Обработка: {'OK' if logs_analysis['process_items_calls'] > 0 else 'FAIL'}")
        print(f"  • Ошибки 403: {'FAIL' if logs_analysis['error_403_count'] > 0 else 'OK'}")
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    if not proxy_link_ok:
        print("❌ Ссылка на прокси не работает - проверьте URL")
    if not config_ok:
        print("❌ Неправильная конфигурация - исправьте настройки прокси")
    if logs_analysis and logs_analysis['error_403_count'] > 0:
        print("❌ Есть ошибки 403 - прокси заблокированы")
    if logs_analysis and logs_analysis['process_items_calls'] == 0:
        print("❌ process_items не выполняется - проблема с планировщиком")
    if logs_analysis and logs_analysis['proxy_mentions'] == 0:
        print("❌ Прокси не используются - проверьте настройки")

if __name__ == "__main__":
    main()