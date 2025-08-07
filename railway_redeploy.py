#!/usr/bin/env python3
"""
Модуль для автоматического редеплоя Railway при проблемах с подключением к Vinted
"""
import os
import time
import threading
import requests
from datetime import datetime, timedelta
from logger import get_logger

# Импортируем конфигурацию Railway
try:
    from railway_config import setup_railway_environment, get_service_id_from_cli
    setup_railway_environment()
    get_service_id_from_cli()
except ImportError:
    pass

logger = get_logger(__name__)

class RailwayRedeployManager:
    """Менеджер автоматического редеплоя Railway"""
    
    def __init__(self):
        self.project_id = os.getenv('RAILWAY_PROJECT_ID', '101cc62f-b314-41d1-9b55-d58ae5c371ea')
        self.service_id = os.getenv('RAILWAY_SERVICE_ID')  # Нужно будет получить
        self.api_token = os.getenv('RAILWAY_TOKEN')
        
        # Отслеживание HTTP ошибок
        self.error_403_count = 0
        self.first_403_time = None
        self.last_403_time = None
        
        self.error_401_count = 0
        self.first_401_time = None
        self.last_401_time = None
        
        self.error_429_count = 0
        self.first_429_time = None
        self.last_429_time = None
        
        self.redeploy_threshold_minutes = 4
        self.max_http_errors = 5  # Минимальное количество HTTP ошибок подряд (любых: 401, 403, 429)
        
        # Защита от частых редеплоев
        self.last_redeploy_time = self._load_last_redeploy_time()
        self.min_redeploy_interval_minutes = 10
        
        self.lock = threading.Lock()
        
        logger.info(f"[REDEPLOY] Initialized Railway Redeploy Manager")
        logger.info(f"[REDEPLOY] Project ID: {self.project_id}")
        logger.info(f"[REDEPLOY] Threshold: {self.redeploy_threshold_minutes} minutes")
        if self.last_redeploy_time:
            logger.info(f"[REDEPLOY] Last redeploy: {self.last_redeploy_time}")
    
    def _load_last_redeploy_time(self):
        """Загрузить время последнего редеплоя из базы данных"""
        try:
            import db
            last_redeploy_str = db.get_parameter("last_redeploy_time")
            if last_redeploy_str and last_redeploy_str != "None":
                return datetime.fromisoformat(last_redeploy_str)
        except Exception as e:
            logger.debug(f"[REDEPLOY] Could not load last redeploy time: {e}")
        return None
    
    def _save_last_redeploy_time(self, redeploy_time):
        """Сохранить время последнего редеплоя в базу данных"""
        try:
            import db
            db.set_parameter("last_redeploy_time", redeploy_time.isoformat())
            logger.info(f"[REDEPLOY] Saved redeploy time to database: {redeploy_time}")
        except Exception as e:
            logger.error(f"[REDEPLOY] Could not save redeploy time: {e}")
    
    def report_403_error(self):
        """Сообщить о получении 403 ошибки"""
        with self.lock:
            current_time = datetime.now()
            
            # Если это первая 403 ошибка или прошло много времени с последней
            if self.first_403_time is None or (current_time - self.last_403_time).total_seconds() > 300:  # 5 минут
                self.first_403_time = current_time
                self.error_403_count = 1
                logger.warning(f"[REDEPLOY] First 403 error detected at {current_time}")
            else:
                self.error_403_count += 1
                logger.warning(f"[REDEPLOY] 403 error #{self.error_403_count} detected at {current_time}")
            
            self.last_403_time = current_time
            
            # Проверяем, нужно ли делать редеплой
            self._check_redeploy_needed()
    
    def report_401_error(self):
        """Сообщить о получении 401 ошибки"""
        with self.lock:
            current_time = datetime.now()
            
            # Если это первая 401 ошибка или прошло много времени с последней
            if self.first_401_time is None or (current_time - self.last_401_time).total_seconds() > 300:  # 5 минут
                self.first_401_time = current_time
                self.error_401_count = 1
                logger.warning(f"[REDEPLOY] First 401 error detected at {current_time}")
            else:
                self.error_401_count += 1
                logger.warning(f"[REDEPLOY] 401 error #{self.error_401_count} detected at {current_time}")
            
            self.last_401_time = current_time
            
            # Проверяем, нужно ли делать редеплой
            self._check_redeploy_needed()
    
    def report_429_error(self):
        """Сообщить о получении 429 ошибки"""
        with self.lock:
            current_time = datetime.now()
            
            # Если это первая 429 ошибка или прошло много времени с последней
            if self.first_429_time is None or (current_time - self.last_429_time).total_seconds() > 300:  # 5 минут
                self.first_429_time = current_time
                self.error_429_count = 1
                logger.warning(f"[REDEPLOY] First 429 error detected at {current_time}")
            else:
                self.error_429_count += 1
                logger.warning(f"[REDEPLOY] 429 error #{self.error_429_count} detected at {current_time}")
            
            self.last_429_time = current_time
            
            # Проверяем, нужно ли делать редеплой
            self._check_redeploy_needed()
    
    def report_success(self):
        """Сообщить об успешном запросе (сбросить счетчики всех ошибок)"""
        with self.lock:
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            if total_errors > 0:
                logger.info(f"[REDEPLOY] Connection restored! Resetting error counters - 403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count}")
                # Сброс 403 ошибок
                self.error_403_count = 0
                self.first_403_time = None
                self.last_403_time = None
                # Сброс 401 ошибок
                self.error_401_count = 0
                self.first_401_time = None
                self.last_401_time = None
                # Сброс 429 ошибок
                self.error_429_count = 0
                self.first_429_time = None
                self.last_429_time = None
    
    def _check_redeploy_needed(self):
        """Проверить, нужен ли редеплой"""
        # Находим самую раннюю ошибку из всех типов
        first_error_times = [t for t in [self.first_403_time, self.first_401_time, self.first_429_time] if t is not None]
        if not first_error_times:
            return
        
        first_error_time = min(first_error_times)
        total_errors = self.error_403_count + self.error_401_count + self.error_429_count
        
        current_time = datetime.now()
        time_since_first_error = current_time - first_error_time
        
        # Условия для редеплоя:
        # 1. Прошло больше threshold_minutes с первой HTTP ошибки (любой: 401, 403, 429)
        # 2. Получено достаточно HTTP ошибок суммарно
        # 3. С последнего редеплоя прошло достаточно времени
        
        if (time_since_first_error.total_seconds() >= self.redeploy_threshold_minutes * 60 and 
            total_errors >= self.max_http_errors):
            
            # Проверяем, не делали ли редеплой недавно
            if (self.last_redeploy_time is None or 
                (current_time - self.last_redeploy_time).total_seconds() >= self.min_redeploy_interval_minutes * 60):
                
                logger.critical(f"[REDEPLOY] Redeploy conditions met:")
                logger.critical(f"[REDEPLOY] - Time since first error: {time_since_first_error}")
                logger.critical(f"[REDEPLOY] - Total HTTP errors: {total_errors} (403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count})")
                logger.critical(f"[REDEPLOY] - Initiating automatic redeploy...")
                
                self._perform_redeploy()
            else:
                time_since_last_redeploy = current_time - self.last_redeploy_time
                logger.warning(f"[REDEPLOY] Redeploy needed but blocked by cooldown. Time since last: {time_since_last_redeploy}")
    
    def _perform_redeploy(self):
        """Выполнить редеплой через Railway API"""
        try:
            if not self.api_token:
                logger.error("[REDEPLOY] Railway API token not found. Cannot perform redeploy.")
                self._fallback_redeploy()
                return
            
            # Railway GraphQL API endpoint
            url = "https://backboard.railway.com/graphql/v2"
            
            # GraphQL mutation для редеплоя
            mutation = """
            mutation serviceRedeploy($serviceId: String!) {
                serviceRedeploy(serviceId: $serviceId) {
                    id
                }
            }
            """
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Если service_id не установлен, пытаемся получить его
            if not self.service_id:
                self.service_id = self._get_service_id()
                if not self.service_id:
                    logger.error("[REDEPLOY] Could not get service ID. Using fallback method.")
                    self._fallback_redeploy()
                    return
            
            payload = {
                "query": mutation,
                "variables": {
                    "serviceId": self.service_id
                }
            }
            
            logger.info(f"[REDEPLOY] Sending redeploy request to Railway API...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "errors" not in result:
                    logger.info("[REDEPLOY] ✅ Railway redeploy initiated successfully!")
                    self.last_redeploy_time = datetime.now()
                    self._save_last_redeploy_time(self.last_redeploy_time)
                    self._reset_error_tracking()
                else:
                    logger.error(f"[REDEPLOY] GraphQL errors: {result.get('errors')}")
                    self._fallback_redeploy()
            else:
                logger.error(f"[REDEPLOY] API request failed: {response.status_code} - {response.text}")
                self._fallback_redeploy()
                
        except Exception as e:
            logger.error(f"[REDEPLOY] Exception during redeploy: {e}")
            self._fallback_redeploy()
    
    def _get_service_id(self):
        """Получить Service ID для текущего проекта"""
        try:
            url = "https://backboard.railway.com/graphql/v2"
            
            query = """
            query project($projectId: String!) {
                project(id: $projectId) {
                    services {
                        edges {
                            node {
                                id
                                name
                            }
                        }
                    }
                }
            }
            """
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "query": query,
                "variables": {
                    "projectId": self.project_id
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                services = result.get("data", {}).get("project", {}).get("services", {}).get("edges", [])
                
                # Ищем основной сервис (обычно первый или с именем содержащим "app", "web", "main")
                for service in services:
                    service_node = service.get("node", {})
                    service_name = service_node.get("name", "").lower()
                    service_id = service_node.get("id")
                    
                    # Приоритет для основного сервиса
                    if any(keyword in service_name for keyword in ["app", "web", "main", "vs5"]):
                        logger.info(f"[REDEPLOY] Found main service: {service_name} ({service_id})")
                        return service_id
                
                # Если не нашли основной, берем первый
                if services:
                    first_service = services[0].get("node", {})
                    service_id = first_service.get("id")
                    service_name = first_service.get("name", "unknown")
                    logger.info(f"[REDEPLOY] Using first service: {service_name} ({service_id})")
                    return service_id
            
            logger.error("[REDEPLOY] Could not retrieve service ID from Railway API")
            return None
            
        except Exception as e:
            logger.error(f"[REDEPLOY] Error getting service ID: {e}")
            return None
    
    def _fallback_redeploy(self):
        """Fallback метод через CLI команду"""
        try:
            logger.info("[REDEPLOY] Attempting fallback redeploy via Railway CLI...")
            
            import subprocess
            
            # Попытка выполнить редеплой через CLI
            result = subprocess.run(
                ["railway", "redeploy", "-y"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.getcwd()
            )
            
            logger.info(f"[REDEPLOY] CLI command result: return_code={result.returncode}")
            logger.info(f"[REDEPLOY] CLI stdout: {result.stdout}")
            logger.info(f"[REDEPLOY] CLI stderr: {result.stderr}")
            
            if result.returncode == 0:
                logger.info("[REDEPLOY] ✅ Railway redeploy via CLI successful!")
                self.last_redeploy_time = datetime.now()
                self._save_last_redeploy_time(self.last_redeploy_time)
                self._reset_error_tracking()
                return True
            else:
                logger.error(f"[REDEPLOY] CLI redeploy failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("[REDEPLOY] CLI redeploy timed out")
            return False
        except FileNotFoundError:
            logger.error("[REDEPLOY] Railway CLI not found in production environment")
            # Пробуем альтернативный метод
            return self._emergency_redeploy()
        except Exception as e:
            logger.error(f"[REDEPLOY] Fallback redeploy failed: {e}")
            return False
    
    def _emergency_redeploy(self):
        """Экстренный метод редеплоя через системный выход"""
        try:
            logger.critical("[REDEPLOY] Using emergency redeploy method - forcing app restart")
            
            # Обновляем время редеплоя
            self.last_redeploy_time = datetime.now()
            self._save_last_redeploy_time(self.last_redeploy_time)
            self._reset_error_tracking()
            
            # Записываем в файл маркер для мониторинга
            try:
                with open('/tmp/redeploy_requested', 'w') as f:
                    f.write(str(self.last_redeploy_time))
                logger.info("[REDEPLOY] Created redeploy marker file")
            except:
                pass
            
            # Принудительно завершаем процесс для перезапуска Railway
            import signal
            import threading
            
            def delayed_exit():
                import time
                time.sleep(2)  # Даем время на отправку ответа
                logger.critical("[REDEPLOY] Forcing application restart...")
                os._exit(1)  # Принудительный выход
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(target=delayed_exit)
            thread.daemon = True
            thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"[REDEPLOY] Emergency redeploy failed: {e}")
            return False
    
    def _reset_error_tracking(self):
        """Сбросить отслеживание ошибок после успешного редеплоя"""
        # Сброс 403 ошибок
        self.error_403_count = 0
        self.first_403_time = None
        self.last_403_time = None
        # Сброс 401 ошибок
        self.error_401_count = 0
        self.first_401_time = None
        self.last_401_time = None
        # Сброс 429 ошибок
        self.error_429_count = 0
        self.first_429_time = None
        self.last_429_time = None
        logger.info("[REDEPLOY] All error tracking reset after redeploy")
    
    def get_status(self):
        """Получить текущий статус системы редеплоя"""
        with self.lock:
            current_time = datetime.now()
            
            # Находим самую раннюю ошибку из всех типов
            first_error_times = [t for t in [self.first_403_time, self.first_401_time, self.first_429_time] if t is not None]
            first_error_time = min(first_error_times) if first_error_times else None
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            
            status = {
                # 403 ошибки
                "error_403_count": self.error_403_count,
                "first_403_time": self.first_403_time.isoformat() if self.first_403_time else None,
                "last_403_time": self.last_403_time.isoformat() if self.last_403_time else None,
                
                # 401 ошибки
                "error_401_count": self.error_401_count,
                "first_401_time": self.first_401_time.isoformat() if self.first_401_time else None,
                "last_401_time": self.last_401_time.isoformat() if self.last_401_time else None,
                
                # 429 ошибки
                "error_429_count": self.error_429_count,
                "first_429_time": self.first_429_time.isoformat() if self.first_429_time else None,
                "last_429_time": self.last_429_time.isoformat() if self.last_429_time else None,
                
                # Общая информация
                "total_errors": total_errors,
                "last_redeploy_time": self.last_redeploy_time.isoformat() if self.last_redeploy_time else None,
                "redeploy_threshold_minutes": self.redeploy_threshold_minutes,
                "max_http_errors": self.max_http_errors
            }
            
            if first_error_time:
                time_since_first = current_time - first_error_time
                status["time_since_first_error_seconds"] = time_since_first.total_seconds()
                status["redeploy_needed"] = (
                    time_since_first.total_seconds() >= self.redeploy_threshold_minutes * 60 and
                    total_errors >= self.max_http_errors
                )
            
            return status

# Глобальный экземпляр менеджера
redeploy_manager = RailwayRedeployManager()

def report_403_error():
    """Функция для сообщения о 403 ошибке"""
    redeploy_manager.report_403_error()

def report_401_error():
    """Функция для сообщения о 401 ошибке"""
    redeploy_manager.report_401_error()

def report_429_error():
    """Функция для сообщения о 429 ошибке"""
    redeploy_manager.report_429_error()

def report_success():
    """Функция для сообщения об успешном запросе"""
    redeploy_manager.report_success()

def get_redeploy_status():
    """Получить статус системы редеплоя"""
    return redeploy_manager.get_status()