#!/usr/bin/env python3
"""
ПРОСТОЙ TELEGRAM ОТПРАВЩИК ДЛЯ VINTED NOTIFICATIONS
Обходит сложную LeRobot систему и работает напрямую с API
"""

import requests
import time
import queue
import threading
from logger import get_logger
import db

logger = get_logger(__name__)

class SimpleTelegramSender:
    def __init__(self, items_queue):
        self.items_queue = items_queue
        self.token = db.get_parameter("telegram_token")
        self.chat_id = db.get_parameter("telegram_chat_id")
        self.running = False
        
        logger.info("SimpleTelegramSender initialized")
        
    def send_message(self, content, url=None, photo_url=None):
        """Send message to Telegram using HTTP API"""
        try:
            api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            
            # Prepare message data
            data = {
                'chat_id': self.chat_id,
                'text': content,
                'parse_mode': 'HTML'
            }
            
            # Add inline keyboard if URL provided
            if url:
                keyboard = {
                    'inline_keyboard': [[
                        {'text': 'Open Vinted', 'url': url}
                    ]]
                }
                data['reply_markup'] = keyboard
            
            # Send message
            response = requests.post(api_url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"✅ Message sent to Telegram successfully!")
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {result}")
                    return False
            else:
                logger.error(f"❌ HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending to Telegram: {e}")
            return False
    
    def start_monitoring(self):
        """Start monitoring the queue for new items"""
        self.running = True
        logger.info("🚀 SimpleTelegramSender started monitoring queue")
        
        while self.running:
            try:
                if not self.items_queue.empty():
                    # Get item from queue
                    queue_item = self.items_queue.get()
                    logger.info(f"📦 Processing queue item: {queue_item}")
                    
                    # Handle different queue formats
                    if len(queue_item) >= 3:
                        content = queue_item[0]
                        url = queue_item[1] if len(queue_item) > 1 else None
                        photo_url = queue_item[6] if len(queue_item) > 6 else None
                        
                        # Send to Telegram
                        logger.info(f"📱 Sending to Telegram: {content[:50]}...")
                        success = self.send_message(content, url, photo_url)
                        
                        if success:
                            logger.info("✅ Item sent to Telegram successfully!")
                        else:
                            logger.error("❌ Failed to send item to Telegram")
                    else:
                        logger.warning(f"⚠️ Invalid queue item format: {queue_item}")
                        
                else:
                    # Queue is empty, wait a bit
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        logger.info("🛑 SimpleTelegramSender stopped")

def start_simple_telegram_sender(items_queue):
    """Start the simple Telegram sender in a thread"""
    try:
        sender = SimpleTelegramSender(items_queue)
        
        # Start monitoring in thread
        monitor_thread = threading.Thread(target=sender.start_monitoring, daemon=True)
        monitor_thread.start()
        
        logger.info("✅ SimpleTelegramSender thread started")
        return sender
        
    except Exception as e:
        logger.error(f"❌ Error starting SimpleTelegramSender: {e}")
        return None

if __name__ == "__main__":
    # Test the sender
    test_queue = queue.Queue()
    
    # Add test item
    test_content = "🧪 <b>ТЕСТ ПРОСТОГО TELEGRAM ОТПРАВЩИКА</b>\n\nЭто тестовое сообщение от простого отправщика!"
    test_queue.put((test_content, "https://vinted.de", "Open Vinted"))
    
    # Start sender
    sender = start_simple_telegram_sender(test_queue)
    
    if sender:
        print("✅ SimpleTelegramSender started!")
        print("📱 Check your Telegram chat for test message")
        
        # Wait for test
        time.sleep(10)
        sender.stop()
    else:
        print("❌ Failed to start SimpleTelegramSender")