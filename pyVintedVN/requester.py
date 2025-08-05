#!/usr/bin/env python3
"""
Рабочий requester с Bearer авторизацией для замены старого requester.py
"""
import requests
import uuid
import random
import time
from logger import get_logger

logger = get_logger(__name__)

class requester:
    """Рабочий Vinted requester с Bearer авторизацией"""
    
    def __init__(self, cookie=None, with_proxy=True, debug=False, headers=None):
        self.debug = debug
        self.session = requests.Session()
        self.access_token = None
        self.MAX_RETRIES = 5
        
        # Базовые headers
        self.HEADER = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors", 
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.vinted.de/",
            "Origin": "https://www.vinted.de",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        
        if headers:
            self.HEADER.update(headers)
            
        self.session.headers.update(self.HEADER)
        
        # Настройка прокси
        if with_proxy:
            self.configure_proxy()
        
        # Получение Bearer токена
        self.get_access_token()
        
        if self.debug:
            logger.info("[DEBUG] Working requester initialized successfully")
    
    def configure_proxy(self):
        """Настройка прокси"""
        try:
            import proxies
            logger.info(f"[DEBUG] Configuring proxy for requester...")
            proxy_configured = proxies.configure_proxy(self.session)
            if proxy_configured:
                logger.info(f"[DEBUG] Proxy configured successfully: {self.session.proxies}")
            else:
                logger.info(f"[DEBUG] No proxy configured - using direct connection")
        except Exception as e:
            logger.error(f"[DEBUG] Proxy configuration failed: {e}")
            import traceback
            logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
    
    def get_access_token(self):
        """Получение access_token_web для Bearer авторизации"""
        try:
            if self.debug:
                logger.info("[DEBUG] Getting access token from main page...")
            
            # Headers для главной страницы
            main_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Временно обновляем headers
            original_headers = dict(self.session.headers)
            self.session.headers.update(main_headers)
            
            # Запрос к главной странице
            response = self.session.get("https://www.vinted.de/", timeout=30)
            
            # Восстанавливаем API headers
            self.session.headers.clear()
            self.session.headers.update(original_headers)
            
            if response.status_code == 200:
                # Извлекаем access_token_web из cookies
                for cookie in self.session.cookies:
                    if cookie.name == 'access_token_web':
                        self.access_token = cookie.value
                        # Добавляем Bearer authorization
                        self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                        if self.debug:
                            logger.info(f"[DEBUG] Bearer token obtained: {self.access_token[:50]}...")
                        return True
                
                if self.debug:
                    logger.info("[DEBUG] No access_token_web found in cookies")
                return False
            else:
                if self.debug:
                    logger.info(f"[DEBUG] Main page request failed: {response.status_code}")
                return False
                
        except Exception as e:
            if self.debug:
                logger.info(f"[DEBUG] Error getting token: {e}")
            return False
    
    def refresh_token_if_needed(self):
        """Обновление токена при необходимости"""
        return self.get_access_token()
    
    def set_cookies(self, cookie=None):
        """Обновление сессии и получение нового токена"""
        if self.debug:
            logger.info("[DEBUG] Refreshing session and token...")
        
        # Очищаем старые cookies и токен
        self.session.cookies.clear()
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        self.access_token = None
        
        # Получаем новый токен
        success = self.get_access_token()
        
        if self.debug:
            logger.info(f"[DEBUG] Token refresh {'successful' if success else 'failed'}")
        
        return success
    
    def set_locale(self, locale):
        """Установка локали (для совместимости)"""
        if self.debug:
            logger.info(f"[DEBUG] Setting locale to: {locale}")
        
        # Обновляем headers для конкретной локали
        locale_headers = {
            "Host": f"{locale}",
            "Referer": f"https://{locale}/",
            "Origin": f"https://{locale}",
        }
        self.session.headers.update(locale_headers)
    
    def get(self, url, params=None):
        """GET запрос с повторными попытками и обновлением токена"""
        if self.debug:
            logger.info(f"[DEBUG] Making GET request to: {url}")
            if params:
                logger.info(f"[DEBUG] Request params: {params}")
        
        tried = 0
        while tried < self.MAX_RETRIES:
            tried += 1
            
            # Добавляем случайную задержку между попытками
            if tried > 1:
                delay = random.uniform(1, 3)
                if self.debug:
                    logger.info(f"[DEBUG] Adding delay of {delay:.2f}s before retry {tried}")
                time.sleep(delay)
            
            try:
                response = self.session.get(url, params=params, timeout=30, allow_redirects=True)
                
                # Increment API request counter
                try:
                    import db
                    db.increment_api_requests()
                except:
                    pass  # Don't fail request if counter fails
                
                if self.debug:
                    logger.info(f"[DEBUG] Request to {url} returned status {response.status_code}")
                
                if response.status_code == 200:
                    return response
                elif response.status_code in (401, 403):
                    if self.debug:
                        logger.info(f"[DEBUG] Auth error {response.status_code}, refreshing token (try {tried}/{self.MAX_RETRIES})")
                    
                    # Пытаемся обновить токен
                    if self.refresh_token_if_needed():
                        if tried < self.MAX_RETRIES:
                            continue  # Пробуем еще раз с новым токеном
                    
                    # Если обновление токена не помогло и это последняя попытка
                    if tried == self.MAX_RETRIES:
                        return response
                else:
                    # Для других ошибок возвращаем ответ
                    return response
                    
            except Exception as e:
                if self.debug:
                    logger.info(f"[DEBUG] Request error (try {tried}/{self.MAX_RETRIES}): {e}")
                
                if tried == self.MAX_RETRIES:
                    raise e
                
                # Ждем перед повторной попыткой
                time.sleep(2)
        
        # Не должно сюда дойти, но на всякий случай
        return response
    
    def post(self, url, data=None, json_data=None):
        """POST запрос (для совместимости)"""
        if self.debug:
            logger.info(f"[DEBUG] Making POST request to: {url}")
        
        try:
            if json_data:
                response = self.session.post(url, json=json_data, timeout=30)
            else:
                response = self.session.post(url, data=data, timeout=30)
            return response
        except Exception as e:
            if self.debug:
                logger.info(f"[DEBUG] POST request error: {e}")
            raise e

# Создаем глобальный экземпляр для совместимости с существующим кодом
_global_requester_instance = None

def get_requester_instance(debug=False):
    """Получение единственного экземпляра requester"""
    global _global_requester_instance
    if _global_requester_instance is None:
        _global_requester_instance = requester(debug=debug)
    return _global_requester_instance

# Создаем глобальный экземпляр для обратной совместимости
requester_instance = get_requester_instance(debug=True)

# Переопределяем requester чтобы он ссылался на экземпляр, а не класс
requester = requester_instance

# Экспортируем все для совместимости
__all__ = ['requester', 'get_requester_instance']