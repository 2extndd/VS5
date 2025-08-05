#!/usr/bin/env python3
"""
Скрипт для прямой проверки прокси в базе данных Railway
"""

import os
import sys

def check_railway_proxies_direct():
    """Проверяем прокси в базе данных Railway напрямую"""
    print("🔍 Прямая проверка прокси в базе данных Railway...")
    print("=" * 50)
    
    # Проверяем переменные окружения Railway
    print("🔍 Проверка переменных окружения:")
    
    # DATABASE_URL для Railway
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print(f"✅ DATABASE_URL найден: {database_url[:50]}...")
        
        # Пытаемся подключиться к базе данных Railway
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            # Парсим DATABASE_URL
            parsed = urlparse(database_url)
            
            # Подключаемся к PostgreSQL
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            
            cursor = conn.cursor()
            
            # Проверяем таблицу parameters
            cursor.execute("SELECT * FROM parameters WHERE parameter_name LIKE '%proxy%'")
            proxy_params = cursor.fetchall()
            
            print(f"\n📋 Найденные параметры прокси в Railway:")
            for param in proxy_params:
                print(f"  • {param[1]}: {param[2][:100]}...")
            
            # Проверяем конкретно proxy_list
            cursor.execute("SELECT parameter_value FROM parameters WHERE parameter_name = 'proxy_list'")
            proxy_list_result = cursor.fetchone()
            
            if proxy_list_result:
                proxy_list_str = proxy_list_result[0]
                print(f"\n📋 Proxy List в Railway:")
                print(f"  • Длина: {len(proxy_list_str)} символов")
                print(f"  • Начало: {proxy_list_str[:100]}...")
                
                # Пытаемся распарсить список прокси
                try:
                    import ast
                    proxy_list = ast.literal_eval(proxy_list_str)
                    print(f"  • Количество прокси: {len(proxy_list)}")
                    print(f"  • Первые 5 прокси:")
                    for i, proxy in enumerate(proxy_list[:5], 1):
                        print(f"    {i}. {proxy}")
                except:
                    print(f"  • Ошибка парсинга списка прокси")
            else:
                print(f"\n❌ Proxy List не найден в Railway")
            
            # Проверяем proxy_list_link
            cursor.execute("SELECT parameter_value FROM parameters WHERE parameter_name = 'proxy_list_link'")
            proxy_link_result = cursor.fetchone()
            
            if proxy_link_result:
                print(f"\n📋 Proxy List Link в Railway:")
                print(f"  • {proxy_link_result[0]}")
            else:
                print(f"\n❌ Proxy List Link не найден в Railway")
            
            conn.close()
            
        except ImportError:
            print("❌ psycopg2 не установлен. Установите: pip install psycopg2-binary")
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных Railway: {e}")
    else:
        print("❌ DATABASE_URL не найден")
        print("💡 Это означает, что скрипт запущен локально, а не на Railway")
    
    print("\n💡 Альтернативные способы проверки:")
    print("1. Откройте https://vs5-production.up.railway.app/config")
    print("2. Проверьте секцию 'Proxy Settings'")
    print("3. Используйте команду: railway logs | grep -i 'proxy'")

if __name__ == "__main__":
    check_railway_proxies_direct() 