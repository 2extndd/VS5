
import sys
import os
sys.path.append('/Users/extndd/Documents/Vinted-Notifications')

import db

print("=== Текущие параметры в базе ===")
try:
    # Подключаемся к локальной базе для проверки параметров
    import sqlite3
    conn = sqlite3.connect('vinted_notifications.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM parameters")
    params = cursor.fetchall()
    
    print(f"Всего параметров: {len(params)}")
    for key, value in params:
        if len(str(value)) > 50:
            print(f"{key}: {str(value)[:50]}...")
        else:
            print(f"{key}: {value}")
    
    conn.close()
    
except Exception as e:
    print(f"Ошибка работы с локальной базой: {e}")

print("
=== Важные параметры для Railway ===")
print("Нужно установить через Web UI:")
print("1. Enable Logging = ВКЛ")
print("2. Refresh Delay = 300 (5 минут)")
print("3. Max Retries = 3")
print("4. Request Timeout = 30")
