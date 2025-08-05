#!/usr/bin/env python3
"""
ПРОСТОЙ БОТ БЕЗ ПЛАНИРОВЩИКОВ И ПРОЦЕССОВ
Работает в одном потоке, делает запросы напрямую
"""
import time
import sys
import os
import db
import core
import queue
import threading
from logger import get_logger

logger = get_logger(__name__)

def scan_worker():
    """Рабочий поток для сканирования"""
    items_queue = queue.Queue()
    
    while True:
        try:
            # Получаем интервал из базы
            delay = db.get_parameter("query_refresh_delay")
            delay_seconds = int(delay) if delay else 30
            
            logger.info(f"🔄 Запуск сканирования (интервал: {delay_seconds}с)")
            
            # Запускаем сканирование
            result = core.process_items(items_queue)
            logger.info(f"✅ Сканирование завершено: {result}")
            
            # Ждем
            logger.info(f"⏳ Ожидание {delay_seconds} секунд...")
            time.sleep(delay_seconds)
            
        except Exception as e:
            logger.error(f"💥 ОШИБКА В СКАНЕРЕ: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            time.sleep(10)  # Ждем 10 сек при ошибке

def main():
    logger.info("🚀 ЗАПУСК ПРОСТОГО БОТА")
    
    # Инициализация базы
    try:
        conn, db_type = db.get_db_connection()
        conn.close()
        logger.info(f"База: {db_type}")
        
        if db_type == 'postgresql':
            db.create_or_update_db("initial_db.sql")
            logger.info("PostgreSQL инициализирована")
    except Exception as e:
        logger.error(f"Ошибка базы: {e}")
        return
    
    # Запускаем сканер в отдельном потоке
    logger.info("🚀 Запуск потока сканирования...")
    scan_thread = threading.Thread(target=scan_worker, daemon=True)
    scan_thread.start()
    
    # Запускаем Web UI в основном потоке
    logger.info("🌐 Запуск Web UI...")
    port = int(os.environ.get('PORT', 8080))
    
    from web_ui_plugin.web_ui import app
    logger.info(f"Web UI стартует на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()