#!/usr/bin/env python3
"""
Рабочий requester с Bearer авторизацией для замены старого requester.py
"""
import requests
import uuid
import random
import time
import sys
import os
from logger import get_logger

# Добавляем путь для импорта модуля редеплоя
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = get_logger(__name__)

# Импортируем систему автоматического редеплоя
try:
    from railway_redeploy import report_403_error, report_401_error, report_429_error, report_success
    REDEPLOY_AVAILABLE = True
    logger.info("[REQUESTER] Railway auto-redeploy system loaded")
except ImportError as e:
    logger.warning(f"[REQUESTER] Railway auto-redeploy system not available: {e}")
    REDEPLOY_AVAILABLE = False
    
    # Заглушки для функций
    def report_403_error():
        pass
    
    def report_401_error():
        pass
    
    def report_429_error():
        pass
    
    def report_success():
        pass

class requester:
    """Рабочий Vinted requester с Bearer авторизацией"""
    
    def __init__(self, cookie=None, with_proxy=True, debug=False, headers=None):
        self.debug = debug
        self.session = requests.Session()
        self.access_token = None
        self.MAX_RETRIES = 5
        self.use_proxy = with_proxy
        self.request_count = 0  # Счетчик запросов
        
        # Получаем интервал ротации прокси из БД
        try:
            import db
            rotation_interval_str = db.get_parameter("proxy_rotation_interval")
            self.proxy_rotation_interval = int(rotation_interval_str) if rotation_interval_str else 1
        except:
            self.proxy_rotation_interval = 1  # По умолчанию менять прокси каждый запрос
        
        if self.debug:
            logger.info(f"[REQUESTER] Proxy rotation interval: {self.proxy_rotation_interval} request(s)")
        
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
    
    def configure_proxy(self, force_new=False):
        """Настройка прокси"""
        try:
            import proxies
            
            # Если force_new=True или это первая настройка, получаем новый случайный прокси
            if force_new or self.request_count == 0:
                logger.info(f"[REQUESTER] Getting random proxy from pool...")
                proxy_configured = proxies.configure_proxy(self.session)
                if proxy_configured:
                    # Маскируем чувствительные данные в логах
                    proxy_info = str(self.session.proxies)
                    if '@' in proxy_info:
                        # Скрываем пароли в логах
                        import re
                        proxy_info = re.sub(r'://[^:]+:[^@]+@', '://***:***@', proxy_info)
                    if self.debug or force_new:
                        logger.info(f"[REQUESTER] ✅ Proxy configured: {proxy_info}")
                    return True
                else:
                    if self.debug or force_new:
                        logger.warning(f"[REQUESTER] ⚠️  No proxy available - will retry on next request")
                    return False
        except Exception as e:
            logger.error(f"[REQUESTER] ❌ Proxy configuration failed: {e}")
            import traceback
            logger.error(f"[REQUESTER] Traceback: {traceback.format_exc()}")
            return False
    
    def set_random_proxy(self):
        """Установить случайный прокси из пула"""
        if not self.use_proxy:
            return False
        
        try:
            import proxies
            # Получаем случайный прокси из пула
            new_proxy = proxies.get_random_proxy()
            if new_proxy:
                # Очищаем старый прокси
                self.session.proxies.clear()
                # Конвертируем и устанавливаем новый
                proxy_dict = proxies.convert_proxy_string_to_dict(new_proxy)
                self.session.proxies.update(proxy_dict)
                
                if self.debug:
                    # Маскируем чувствительные данные
                    proxy_info = str(proxy_dict)
                    if '@' in proxy_info:
                        import re
                        proxy_info = re.sub(r'://[^:]+:[^@]+@', '://***:***@', proxy_info)
                    logger.info(f"[PROXY] Random proxy set: {proxy_info}")
                return True
            else:
                # Нет новых прокси - СОХРАНЯЕМ текущий прокси, НЕ переходим на direct!
                logger.warning(f"[PROXY] No new proxy available - keeping current proxy configuration")
                return False
        except Exception as e:
            logger.error(f"[PROXY] Error setting random proxy: {e}")
            return False
    
    def rotate_proxy(self):
        """Переключение на новый прокси при проблемах с текущим"""
        try:
            import proxies
            logger.info(f"[PROXY] Rotating to new proxy due to connection issues...")
            
            # Получаем новый прокси (принудительно, без кэша)
            new_proxy = proxies.get_fresh_proxy()
            if new_proxy:
                # Очищаем старые настройки прокси
                self.session.proxies.clear()
                
                # Настраиваем новый прокси
                proxy_configured = proxies.configure_proxy(self.session, new_proxy)
                if proxy_configured:
                    logger.info(f"[PROXY] Successfully rotated to new proxy: {self.session.proxies}")
                    return True
                else:
                    logger.warning(f"[PROXY] Failed to configure new proxy")
            else:
                logger.warning(f"[PROXY] No alternative proxy available for rotation")
                # СОХРАНЯЕМ текущий прокси, НЕ переходим на direct!
                logger.info(f"[PROXY] Keeping current proxy configuration")
            
            return False
        except Exception as e:
            logger.error(f"[PROXY] Proxy rotation failed: {e}")
            return False
    
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
        # Увеличиваем счетчик запросов
        self.request_count += 1
        
        # Устанавливаем случайный прокси перед каждым запросом (если включено)
        if self.use_proxy and self.request_count % self.proxy_rotation_interval == 0:
            self.set_random_proxy()
            if self.debug:
                logger.info(f"[PROXY] Rotated to random proxy (request #{self.request_count})")
        
        if self.debug:
            logger.info(f"[DEBUG] Making GET request to: {url} (request #{self.request_count})")
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
                    # Сообщаем об успешном запросе для сброса счетчика 403 ошибок
                    if REDEPLOY_AVAILABLE:
                        report_success()
                    return response
                elif response.status_code in (401, 403):
                    if self.debug:
                        logger.info(f"[DEBUG] Auth error {response.status_code}, refreshing token (try {tried}/{self.MAX_RETRIES})")
                    
                    # Сообщаем системе автоматического редеплоя о соответствующей ошибке
                    if REDEPLOY_AVAILABLE:
                        if response.status_code == 401:
                            report_401_error()
                            logger.warning(f"[REQUESTER] 401 Unauthorized error reported to redeploy system")
                        elif response.status_code == 403:
                            report_403_error()
                            logger.warning(f"[REQUESTER] 403 Forbidden error reported to redeploy system")
                    
                    # При 403 ошибке пытаемся сменить прокси
                    if response.status_code == 403 and tried <= 2:  # Пытаемся сменить прокси в первых 2 попытках
                        logger.info(f"[REQUESTER] 403 error - attempting proxy rotation (try {tried})")
                        if self.rotate_proxy():
                            logger.info(f"[REQUESTER] Proxy rotated successfully, retrying request")
                            continue  # Пробуем еще раз с новым прокси
                        else:
                            logger.warning(f"[REQUESTER] Proxy rotation failed, continuing with token refresh")
                    
                    # Пытаемся обновить токен
                    if self.refresh_token_if_needed():
                        if tried < self.MAX_RETRIES:
                            continue  # Пробуем еще раз с новым токеном
                    
                    # Если обновление токена не помогло и это последняя попытка
                    if tried == self.MAX_RETRIES:
                        # Еще раз сообщаем об ошибке перед возвратом
                        if REDEPLOY_AVAILABLE:
                            if response.status_code == 401:
                                report_401_error()
                            elif response.status_code == 403:
                                report_403_error()
                        return response
                elif response.status_code == 429:
                    # Too Many Requests - сообщаем системе редеплоя
                    if REDEPLOY_AVAILABLE:
                        report_429_error()
                        logger.warning(f"[REQUESTER] 429 Too Many Requests error reported to redeploy system")
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