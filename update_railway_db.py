import os
import sys
import psycopg2
from urllib.parse import urlparse

# Получаем DATABASE_URL из переменных окружения Railway
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print('❌ DATABASE_URL не найден')
    sys.exit(1)

print(f'📡 Подключаемся к базе: {database_url[:30]}...')

try:
    # Парсим URL базы данных
    url = urlparse(database_url)
    
    # Подключаемся к PostgreSQL
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.path[1:]  # убираем начальный /
    )
    
    cursor = conn.cursor()
    
    print('✅ Подключение успешно!')
    
    # Проверяем текущие параметры
    cursor.execute('SELECT key, value FROM parameters')
    current_params = dict(cursor.fetchall())
    
    print('\n📋 Текущие параметры:')
    for key, value in current_params.items():
        if len(str(value)) > 50:
            print(f'  {key}: {str(value)[:50]}...')
        else:
            print(f'  {key}: {value}')
    
    # Устанавливаем нужные параметры
    updates = {
        'enable_logging': 'True',
        'query_refresh_delay': '300',  # 5 минут
        'max_retries': '3',
        'request_timeout': '30',
        'items_per_query': '2'
    }
    
    print('\n🔧 Обновляем параметры...')
    
    for key, value in updates.items():
        cursor.execute('''
            INSERT INTO parameters (key, value) 
            VALUES (%s, %s) 
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value
        ''', (key, value))
        print(f'  ✅ {key} = {value}')
    
    # Сохраняем изменения
    conn.commit()
    
    print('\n🎉 ВСЕ ПАРАМЕТРЫ ОБНОВЛЕНЫ!')
    print('Теперь нужно перезапустить сервис')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Ошибка: {e}')
    sys.exit(1)