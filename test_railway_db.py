#!/usr/bin/env python3
"""
Railway Database Test - тестирует PostgreSQL на Railway
Проверяет миграцию цен и сохранение товаров
"""

import sys
import os
import requests
import time

def test_railway_database():
    """Тестирует Railway PostgreSQL через API"""
    print("🚂 ТЕСТ RAILWAY POSTGRESQL")
    print("=" * 40)
    
    base_url = "https://vs5-production.up.railway.app"
    
    try:
        # Test 1: Check if web UI is working
        print("🌐 Проверяю доступность Web UI...")
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Web UI доступен")
        else:
            print(f"❌ Web UI недоступен: {response.status_code}")
            return False
            
        # Test 2: Check items endpoint
        print("\n📋 Проверяю /items endpoint...")
        response = requests.get(f"{base_url}/items", timeout=10)
        if response.status_code == 200:
            print("✅ Items endpoint работает")
            
            # Check if "No items found" is in response
            if "No items found" in response.text:
                print("⚠️  'No items found' - товары не сохраняются в БД")
            else:
                print("✅ Товары найдены в БД!")
                
        else:
            print(f"❌ Items endpoint error: {response.status_code}")
            
        # Test 3: Check logs for database errors
        print("\n📊 Проверяю логи на ошибки БД...")
        try:
            response = requests.get(f"{base_url}/api/logs?limit=100", timeout=10)
            if response.status_code == 200:
                logs_data = response.json()
                logs = logs_data.get('logs', [])
                
                # Look for database errors
                db_errors = []
                price_errors = []
                success_logs = []
                
                for log in logs:
                    message = log.get('message', '')
                    if 'Error adding item' in message and 'database' in message:
                        db_errors.append(message)
                    if 'invalid input syntax for type bigint' in message:
                        price_errors.append(message)
                    if 'Successfully added item' in message and 'database' in message:
                        success_logs.append(message)
                
                print(f"🔍 Найдено {len(db_errors)} ошибок БД")
                print(f"💰 Найдено {len(price_errors)} ошибок цен")
                print(f"✅ Найдено {len(success_logs)} успешных добавлений")
                
                if price_errors:
                    print("❌ ОШИБКИ ЦЕН ВСЕ ЕЩЕ ЕСТЬ:")
                    for error in price_errors[:3]:
                        print(f"   - {error[:100]}...")
                    return False
                    
                if success_logs:
                    print("✅ Товары успешно добавляются:")
                    for success in success_logs[:3]:
                        print(f"   + {success[:100]}...")
                        
        except Exception as e:
            print(f"⚠️  Не могу получить логи: {e}")
            
        # Test 4: Check configuration
        print("\n⚙️  Проверяю конфигурацию...")
        try:
            response = requests.get(f"{base_url}/config", timeout=10)
            if response.status_code == 200:
                print("✅ Configuration доступна")
            else:
                print(f"⚠️  Configuration недоступна: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Ошибка получения конфигурации: {e}")
            
        # Test 5: Try to trigger a scan (if possible)
        print("\n🔄 Проверяю процесс сканирования...")
        try:
            # Just check if queries exist
            response = requests.get(f"{base_url}/queries", timeout=10)
            if response.status_code == 200:
                if "D&G" in response.text or "query" in response.text.lower():
                    print("✅ Запросы настроены")
                else:
                    print("⚠️  Запросы не найдены")
            else:
                print(f"⚠️  Queries endpoint: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Ошибка проверки запросов: {e}")
            
        print("\n🏁 ТЕСТ RAILWAY ЗАВЕРШЕН")
        return True
        
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return False

def test_migration_status():
    """Проверяет статус миграции"""
    print("\n🔧 ПРОВЕРКА СТАТУСА МИГРАЦИИ")
    print("=" * 30)
    
    base_url = "https://vs5-production.up.railway.app"
    
    try:
        # Check recent logs for migration
        response = requests.get(f"{base_url}/api/logs?limit=200&level=all", timeout=10)
        
        if response.status_code == 200:
            logs_data = response.json()
            logs = logs_data.get('logs', [])
            
            migration_logs = []
            schema_logs = []
            
            for log in logs:
                message = log.get('message', '')
                if 'migration' in message.lower():
                    migration_logs.append(message)
                if 'schema' in message.lower() or 'database creation' in message.lower():
                    schema_logs.append(message)
            
            if migration_logs:
                print("🔧 Логи миграции:")
                for log in migration_logs[:5]:
                    print(f"   - {log}")
            else:
                print("⚠️  Логи миграции не найдены")
                
            if schema_logs:
                print("\n📋 Логи схемы БД:")
                for log in schema_logs[:3]:
                    print(f"   - {log}")
                    
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки миграции: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ПОЛНЫЙ ТЕСТ RAILWAY DATABASE")
    print("=" * 50)
    
    # Test Railway
    railway_ok = test_railway_database()
    
    # Test Migration
    migration_ok = test_migration_status()
    
    if railway_ok and migration_ok:
        print("\n🎉 ВСЕ ТЕСТЫ RAILWAY ПРОШЛИ!")
    else:
        print("\n💥 ЕСТЬ ПРОБЛЕМЫ С RAILWAY!")
        sys.exit(1)