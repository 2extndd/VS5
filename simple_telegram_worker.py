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
        self.last_update_id = 0  # For processing Telegram updates
        
        logger.info("SimpleTelegramSender initialized with command handling")
        
    def send_message(self, content, url=None, photo_url=None, thread_id=None):
        """Send message to Telegram using HTTP API with thread support and photo attachments"""
        try:
            # If photo_url is provided, send as photo with caption
            if photo_url:
                api_url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
                
                # Prepare photo data
                data = {
                    'chat_id': self.chat_id,
                    'photo': photo_url,
                    'caption': content,
                    'parse_mode': 'HTML'
                }
                
                # Add thread_id if provided (for topics/forums)
                if thread_id:
                    data['message_thread_id'] = int(thread_id)
                    logger.info(f"📍 Sending PHOTO to thread_id: {thread_id}")
                else:
                    logger.info("📍 Sending PHOTO to main chat (no thread_id)")
                
                # Add inline keyboard if URL provided
                if url:
                    keyboard = {
                        'inline_keyboard': [[
                            {'text': 'Open Vinted', 'url': url}
                        ]]
                    }
                    data['reply_markup'] = keyboard
                
            else:
                # Send as regular text message
                api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                
                # Prepare message data
                data = {
                    'chat_id': self.chat_id,
                    'text': content,
                    'parse_mode': 'HTML'
                }
                
                # Add thread_id if provided (for topics/forums)
                if thread_id:
                    data['message_thread_id'] = int(thread_id)
                    logger.info(f"📍 Sending TEXT to thread_id: {thread_id}")
                else:
                    logger.info("📍 Sending TEXT to main chat (no thread_id)")
                
                # Add inline keyboard if URL provided
                if url:
                    keyboard = {
                        'inline_keyboard': [[
                            {'text': 'Open Vinted', 'url': url}
                        ]]
                    }
                    data['reply_markup'] = keyboard
            
            # Send message (photo or text)
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
                # Process incoming Telegram commands
                self.process_telegram_updates()
                
                if not self.items_queue.empty():
                    # Get item from queue
                    queue_item = self.items_queue.get()
                    logger.info(f"📦 Processing queue item: {queue_item}")
                    
                    # Handle different queue formats: (content, url, text, buy_url, buy_text, thread_id, photo_url)
                    if len(queue_item) >= 3:
                        content = queue_item[0]
                        url = queue_item[1] if len(queue_item) > 1 else None
                        thread_id = queue_item[5] if len(queue_item) > 5 else None
                        photo_url = queue_item[6] if len(queue_item) > 6 else None
                        
                        # Send to Telegram with thread_id
                        logger.info(f"📱 Sending to Telegram: {content[:50]}... (thread_id: {thread_id})")
                        success = self.send_message(content, url, photo_url, thread_id)
                        
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
    
    def process_telegram_updates(self):
        """Check for incoming Telegram messages and process commands"""
        try:
            # Get updates from Telegram
            url = f"https://api.telegram.org/bot{self.token}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 1,  # Short timeout for non-blocking
                'limit': 10
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        self.last_update_id = update['update_id']
                        
                        # Process message if present
                        if 'message' in update:
                            self.handle_message(update['message'])
                            
        except Exception as e:
            logger.warning(f"⚠️ Error processing Telegram updates: {e}")
    
    def handle_message(self, message):
        """Handle incoming Telegram message and process commands"""
        try:
            text = message.get('text', '')
            chat_id = message.get('chat', {}).get('id')
            
            # Only process messages from our configured chat
            if str(chat_id) != str(self.chat_id):
                return
                
            # Process commands
            if text.startswith('/'):
                self.handle_command(text, message)
                
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    def handle_command(self, command_text, message):
        """Handle specific Telegram commands"""
        try:
            command = command_text.split()[0].lower()
            
            if command == '/hello':
                self.send_simple_message("🤖 <b>Vinted Bot is running!</b>\n\n✅ Bot is active and monitoring queries.")
                
            elif command == '/app':
                web_url = "https://vs5-production.up.railway.app"
                keyboard = {
                    'inline_keyboard': [[{
                        'text': '🌐 Open Web Interface',
                        'web_app': {'url': web_url}
                    }]]
                }
                self.send_simple_message(
                    "🌐 <b>Vinted Web Interface</b>\n\n"
                    "Click the button below to open the web interface:",
                    keyboard
                )
                
            elif command == '/queries':
                # Get queries from database
                queries = db.get_queries()
                if queries:
                    response = "📋 <b>Active Queries:</b>\n\n"
                    for i, query in enumerate(queries, 1):
                        query_name = query[3] if query[3] else f"Query {i}"
                        thread_id = f" (Thread: {query[4]})" if query[4] else ""
                        response += f"{i}. <b>{query_name}</b>{thread_id}\n"
                else:
                    response = "📋 <b>No active queries found.</b>\n\nAdd queries via Web UI."
                    
                self.send_simple_message(response)
                
            elif command in ['/add_query', '/remove_query', '/allowlist', '/clear_allowlist', '/add_country', '/remove_country']:
                self.send_simple_message(
                    f"ℹ️ <b>Command: {command}</b>\n\n"
                    "This command is available via Web Interface:\n"
                    "🌐 https://vs5-production.up.railway.app\n\n"
                    "Use /app to open the Web UI."
                )
                
            else:
                self.send_simple_message(
                    "❓ <b>Unknown command</b>\n\n"
                    "Available commands:\n"
                    "• /hello - Check bot status\n"
                    "• /app - Open Web Interface\n"
                    "• /queries - List active queries\n\n"
                    "For more features, use /app to open Web UI."
                )
                
        except Exception as e:
            logger.error(f"❌ Error handling command {command_text}: {e}")
            self.send_simple_message("❌ <b>Error processing command</b>\n\nPlease try again.")
    
    def send_simple_message(self, text, keyboard=None):
        """Send a simple text message (for commands)"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            if keyboard:
                import json
                data['reply_markup'] = json.dumps(keyboard)
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"✅ Command response sent: {text[:50]}...")
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {result}")
            else:
                logger.error(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error sending command response: {e}")
        
        return False

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