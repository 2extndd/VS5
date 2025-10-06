#!/usr/bin/env python3
"""
Модуль для автоматического редеплоя Railway при проблемах с подключением к Vinted
"""
import os
import time
import threading
import requests
from datetime import datetime, timedelta, timezone
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
        
        # Счетчик успешных запросов подряд
        self.success_streak = 0
        self.success_threshold = 10  # Сбрасываем ошибки после 10 успешных запросов подряд
        
        # Загружаем параметры из БД или используем значения по умолчанию
        self.redeploy_threshold_minutes = self._get_redeploy_threshold()
        self.max_http_errors = self._get_max_http_errors()
        
        # Защита от частых редеплоев
        self.last_redeploy_time = self._load_last_redeploy_time()
        self.min_redeploy_interval_minutes = 3  # Изменено с 10 на 3 минуты
        
        self.lock = threading.Lock()
        
        logger.info(f"[REDEPLOY] Initialized Railway Redeploy Manager")
        logger.info(f"[REDEPLOY] Project ID: {self.project_id}")
        logger.info(f"[REDEPLOY] Threshold: {self.redeploy_threshold_minutes} minutes")
        if self.last_redeploy_time:
            logger.info(f"[REDEPLOY] Last redeploy: {self.last_redeploy_time}")
    
    def _get_redeploy_threshold(self):
        """Получить порог редеплоя из БД"""
        try:
            import db
            threshold_str = db.get_parameter("redeploy_threshold_minutes")
            if threshold_str:
                return int(threshold_str)
        except Exception as e:
            logger.debug(f"[REDEPLOY] Could not load threshold from DB: {e}")
        return 4  # По умолчанию 4 минуты
    
    def _get_max_http_errors(self):
        """Получить максимальное количество ошибок из БД"""
        try:
            import db
            errors_str = db.get_parameter("max_http_errors")
            if errors_str:
                return int(errors_str)
        except Exception as e:
            logger.debug(f"[REDEPLOY] Could not load max_http_errors from DB: {e}")
        return 5  # По умолчанию 5 ошибок
    
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
            # Сбрасываем счетчик успешных запросов при ошибке
            self.success_streak = 0
            
            current_time = datetime.now(timezone(timedelta(hours=3)))
            
            # Если это первая 403 ошибка или прошло много времени с последней
            if self.first_403_time is None or (current_time - self.last_403_time).total_seconds() > 300:  # 5 минут
                self.first_403_time = current_time
                self.error_403_count = 1
                logger.warning(f"[REDEPLOY] First 403 error detected at {current_time}")
            else:
                self.error_403_count += 1
                logger.warning(f"[REDEPLOY] 403 error #{self.error_403_count} detected at {current_time}")
            
            self.last_403_time = current_time
            
            # Логируем каждые 10 ошибок
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            if total_errors % 10 == 0:
                logger.warning(f"[REDEPLOY] 📊 Total errors reached: {total_errors} (403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count})")
            
            # Проверяем, нужно ли делать редеплой
            self._check_redeploy_needed()
    
    def report_401_error(self):
        """Сообщить о получении 401 ошибки"""
        with self.lock:
            # Сбрасываем счетчик успешных запросов при ошибке
            self.success_streak = 0
            
            current_time = datetime.now(timezone(timedelta(hours=3)))
            
            # Если это первая 401 ошибка или прошло много времени с последней
            if self.first_401_time is None or (current_time - self.last_401_time).total_seconds() > 300:  # 5 минут
                self.first_401_time = current_time
                self.error_401_count = 1
                logger.warning(f"[REDEPLOY] First 401 error detected at {current_time}")
            else:
                self.error_401_count += 1
                logger.warning(f"[REDEPLOY] 401 error #{self.error_401_count} detected at {current_time}")
            
            self.last_401_time = current_time
            
            # Логируем каждые 10 ошибок
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            if total_errors % 10 == 0:
                logger.warning(f"[REDEPLOY] 📊 Total errors reached: {total_errors} (403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count})")
            
            # Проверяем, нужно ли делать редеплой
            self._check_redeploy_needed()
    
    def report_429_error(self):
        """Сообщить о получении 429 ошибки"""
        with self.lock:
            # Сбрасываем счетчик успешных запросов при ошибке
            self.success_streak = 0
            
            current_time = datetime.now(timezone(timedelta(hours=3)))
            
            # Если это первая 429 ошибка или прошло много времени с последней
            if self.first_429_time is None or (current_time - self.last_429_time).total_seconds() > 300:  # 5 минут
                self.first_429_time = current_time
                self.error_429_count = 1
                logger.warning(f"[REDEPLOY] First 429 error detected at {current_time}")
            else:
                self.error_429_count += 1
                logger.warning(f"[REDEPLOY] 429 error #{self.error_429_count} detected at {current_time}")
            
            self.last_429_time = current_time
            
            # Логируем каждые 10 ошибок
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            if total_errors % 10 == 0:
                logger.warning(f"[REDEPLOY] 📊 Total errors reached: {total_errors} (403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count})")
            
            # Проверяем, нужно ли делать редеплой
            self._check_redeploy_needed()
    
    def report_success(self):
        """Сообщить об успешном запросе"""
        with self.lock:
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            
            # Увеличиваем счетчик успешных запросов подряд
            self.success_streak += 1
            
            # Сбрасываем счетчики ошибок ТОЛЬКО после нескольких успешных запросов подряд
            if total_errors > 0 and self.success_streak >= self.success_threshold:
                logger.info(f"[REDEPLOY] ✅ {self.success_threshold} successful requests in a row!")
                logger.info(f"[REDEPLOY] Resetting error counters - 403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count}")
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
                # Сбрасываем streak
                self.success_streak = 0
    
    def _check_redeploy_needed(self):
        """Проверить, нужен ли редеплой"""
        # Находим самую раннюю ошибку из всех типов
        first_error_times = [t for t in [self.first_403_time, self.first_401_time, self.first_429_time] if t is not None]
        if not first_error_times:
            return
        
        first_error_time = min(first_error_times)
        total_errors = self.error_403_count + self.error_401_count + self.error_429_count
        
        current_time = datetime.now(timezone(timedelta(hours=3)))
        time_since_first_error = current_time - first_error_time
        
        # Логируем текущее состояние при каждой проверке (если есть ошибки)
        if total_errors >= 50:  # Логируем только если накопилось много
            logger.info(f"[REDEPLOY] Check: {total_errors} errors, {time_since_first_error.total_seconds():.0f}s since first, success_streak: {self.success_streak}")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Если накопилось 100+ ошибок - редеплоим НЕМЕДЛЕННО!
        if total_errors >= 100:
            logger.critical(f"[REDEPLOY] ════════════════════════════════════════")
            logger.critical(f"[REDEPLOY] 🚨 CRITICAL THRESHOLD REACHED!")
            logger.critical(f"[REDEPLOY] Total errors: {total_errors}")
            logger.critical(f"[REDEPLOY] - 403 errors: {self.error_403_count}")
            logger.critical(f"[REDEPLOY] - 401 errors: {self.error_401_count}")
            logger.critical(f"[REDEPLOY] - 429 errors: {self.error_429_count}")
            logger.critical(f"[REDEPLOY] - Time since first error: {time_since_first_error}")
            logger.critical(f"[REDEPLOY] - Success streak: {self.success_streak}")
            logger.critical(f"[REDEPLOY] - Last redeploy: {self.last_redeploy_time}")
            logger.critical(f"[REDEPLOY] 🚨 Forcing IMMEDIATE redeploy (bypassing cooldown)!")
            logger.critical(f"[REDEPLOY] ════════════════════════════════════════")
            self._perform_redeploy()
            return
        
        # Условия для редеплоя:
        # 1. Прошло больше threshold_minutes с первой HTTP ошибки (любой: 401, 403, 429)
        # 2. Получено достаточно HTTP ошибок суммарно
        # 3. С последнего редеплоя прошло достаточно времени
        
        if (time_since_first_error.total_seconds() >= self.redeploy_threshold_minutes * 60 and 
            total_errors >= self.max_http_errors):
            
            # Проверяем, не делали ли редеплой недавно
            if (self.last_redeploy_time is None or 
                (current_time - self.last_redeploy_time).total_seconds() >= self.min_redeploy_interval_minutes * 60):
                
                logger.critical(f"[REDEPLOY] ════════════════════════════════════════")
                logger.critical(f"[REDEPLOY] ⚠️  NORMAL REDEPLOY CONDITIONS MET")
                logger.critical(f"[REDEPLOY] - Time since first error: {time_since_first_error} (threshold: {self.redeploy_threshold_minutes}min)")
                logger.critical(f"[REDEPLOY] - Total errors: {total_errors} (threshold: {self.max_http_errors})")
                logger.critical(f"[REDEPLOY]   * 403 errors: {self.error_403_count}")
                logger.critical(f"[REDEPLOY]   * 401 errors: {self.error_401_count}")
                logger.critical(f"[REDEPLOY]   * 429 errors: {self.error_429_count}")
                logger.critical(f"[REDEPLOY] - Success streak: {self.success_streak}")
                logger.critical(f"[REDEPLOY] - Last redeploy: {self.last_redeploy_time}")
                logger.critical(f"[REDEPLOY] ⚠️  Initiating automatic redeploy...")
                logger.critical(f"[REDEPLOY] ════════════════════════════════════════")
                
                self._perform_redeploy()
            else:
                time_since_last_redeploy = current_time - self.last_redeploy_time
                logger.warning(f"[REDEPLOY] ⏸️  Redeploy needed but blocked by cooldown")
                logger.warning(f"[REDEPLOY] - Time since last redeploy: {time_since_last_redeploy} (need {self.min_redeploy_interval_minutes}min)")
                logger.warning(f"[REDEPLOY] - Current errors: {total_errors} (403:{self.error_403_count}, 401:{self.error_401_count}, 429:{self.error_429_count})")
    
    def _perform_redeploy(self):
        """Выполнить редеплой через Railway API"""
        try:
            logger.info("[REDEPLOY] 🔄 _perform_redeploy() called")
            logger.info("[REDEPLOY] ════════════════════════════════════════")
            logger.info("[REDEPLOY] 🚀 Attempting GRACEFUL redeploy (no crash!)")

            # Детальная диагностика
            logger.info(f"[REDEPLOY] Project ID: {self.project_id}")
            logger.info(f"[REDEPLOY] Service ID: {self.service_id}")
            logger.info(f"[REDEPLOY] API Token: {self.api_token[:10]}..." if self.api_token else "[REDEPLOY] ❌ No API token")

            if not self.api_token:
                logger.error("[REDEPLOY] ❌ Railway API token not found in environment")
                logger.info("[REDEPLOY] Falling back to alternative redeploy methods...")
                self._fallback_redeploy()
                return

            # Если service_id не установлен, пытаемся получить его
            if not self.service_id:
                logger.info("[REDEPLOY] Service ID not set, trying to get it from API...")
                self.service_id = self._get_service_id()
                if not self.service_id:
                    logger.error("[REDEPLOY] Could not get service ID. Using fallback method.")
                    self._fallback_redeploy()
                    return

            logger.info(f"[REDEPLOY] ✅ All credentials ready - Project: {self.project_id}, Service: {self.service_id}")

            # Railway GraphQL API endpoint
            url = "https://backboard.railway.com/graphql/v2"

            # GraphQL mutation для редеплоя (улучшенная версия)
            mutation = """
            mutation serviceRedeploy($serviceId: String!) {
                serviceRedeploy(serviceId: $serviceId) {
                    id
                    name
                    status
                }
            }
            """

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "RailwayRedeployManager/1.0"
            }

            payload = {
                "query": mutation,
                "variables": {
                    "serviceId": self.service_id
                }
            }

            logger.info(f"[REDEPLOY] 📡 Sending GraphQL mutation to {url}")
            logger.info(f"[REDEPLOY] Mutation: serviceRedeploy({self.service_id})")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            logger.info(f"[REDEPLOY] 📨 Response status: {response.status_code}")
            logger.info(f"[REDEPLOY] 📨 Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[REDEPLOY] 📨 Response JSON keys: {list(result.keys())}")

                # Проверить ошибки в GraphQL ответе
                if "errors" in result:
                    logger.error(f"[REDEPLOY] ❌ GraphQL errors: {result['errors']}")
                    logger.error(f"[REDEPLOY] Full response: {result}")
                    self._fallback_redeploy()
                    return

                # Проверить успешный ответ
                data = result.get("data", {})
                service_redeploy = data.get("serviceRedeploy", {})

                if service_redeploy and service_redeploy.get("id"):
                    service_id = service_redeploy.get("id")
                    service_name = service_redeploy.get("name", "unknown")
                    service_status = service_redeploy.get("status", "unknown")

                    logger.info("[REDEPLOY] ════════════════════════════════════════")
                    logger.info(f"[REDEPLOY] ✅ Railway redeploy initiated successfully!")
                    logger.info(f"[REDEPLOY] 🔄 Service: {service_name} ({service_id})")
                    logger.info(f"[REDEPLOY] 📊 Status: {service_status}")
                    logger.info("[REDEPLOY] 🔄 Service will restart gracefully (NO CRASH)")
                    logger.info("[REDEPLOY] ⏱️  Expected downtime: ~30-60 seconds")
                    logger.info("[REDEPLOY] ════════════════════════════════════════")

                    self.last_redeploy_time = datetime.now(timezone(timedelta(hours=3)))
                    self._save_last_redeploy_time(self.last_redeploy_time)
                    self._reset_error_tracking()

                    # Показать статус в Web UI
                    logger.info(f"[REDEPLOY] 💡 Check Railway dashboard for deployment status")
                else:
                    logger.error(f"[REDEPLOY] ❌ No service redeploy data in response: {result}")
                    self._fallback_redeploy()

            elif response.status_code == 401:
                logger.error(f"[REDEPLOY] ❌ Authentication failed (401) - check API token permissions")
                logger.error(f"[REDEPLOY] Token: {self.api_token[:20]}...")
                self._fallback_redeploy()
            elif response.status_code == 403:
                logger.error(f"[REDEPLOY] ❌ Forbidden (403) - token doesn't have redeploy permissions")
                self._fallback_redeploy()
            elif response.status_code == 404:
                logger.error(f"[REDEPLOY] ❌ Not found (404) - check service ID: {self.service_id}")
                self._fallback_redeploy()
            else:
                logger.error(f"[REDEPLOY] ❌ API request failed: {response.status_code}")
                logger.error(f"[REDEPLOY] Response: {response.text}")
                self._fallback_redeploy()

        except Exception as e:
            logger.error(f"[REDEPLOY] ❌ Exception during API redeploy: {e}")
            import traceback
            logger.error(f"[REDEPLOY] Traceback: {traceback.format_exc()}")
            self._fallback_redeploy()
    
    def _get_service_id(self):
        """Получить Service ID для текущего проекта"""
        try:
            logger.info(f"[REDEPLOY] Getting service ID from Railway API...")
            logger.info(f"[REDEPLOY] Project ID: {self.project_id}")
            logger.info(f"[REDEPLOY] API Token: {self.api_token[:10]}..." if self.api_token else "[REDEPLOY] No API token")

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

            logger.info(f"[REDEPLOY] Making GraphQL request to {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            logger.info(f"[REDEPLOY] GraphQL response status: {response.status_code}")
            logger.info(f"[REDEPLOY] GraphQL response: {response.text[:500]}...")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[REDEPLOY] GraphQL result keys: {list(result.keys())}")

                # Проверить ошибки в GraphQL ответе
                if "errors" in result:
                    logger.error(f"[REDEPLOY] GraphQL errors: {result['errors']}")
                    return None

                services = result.get("data", {}).get("project", {}).get("services", {}).get("edges", [])
                logger.info(f"[REDEPLOY] Found {len(services)} services")

                # Ищем основной сервис (обычно первый или с именем содержащим "app", "web", "main")
                for service in services:
                    service_node = service.get("node", {})
                    service_name = service_node.get("name", "").lower()
                    service_id = service_node.get("id")

                    logger.info(f"[REDEPLOY] Checking service: {service_name} ({service_id})")

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

            logger.error(f"[REDEPLOY] Could not retrieve service ID - HTTP {response.status_code}")
            logger.error(f"[REDEPLOY] Response: {response.text}")
            return None

        except Exception as e:
            logger.error(f"[REDEPLOY] Error getting service ID: {e}")
            import traceback
            logger.error(f"[REDEPLOY] Traceback: {traceback.format_exc()}")
            return None
    
    def _fallback_redeploy(self):
        """Fallback метод через CLI команду"""
        try:
            logger.info("[REDEPLOY] 🔧 Attempting fallback redeploy via Railway CLI...")
            logger.info(f"[REDEPLOY] Current working directory: {os.getcwd()}")

            import subprocess

            # Проверяем, установлен ли Railway CLI
            try:
                check_result = subprocess.run(
                    ["railway", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                logger.info(f"[REDEPLOY] Railway CLI version: {check_result.stdout.strip()}")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                logger.warning(f"[REDEPLOY] Railway CLI check failed: {e}")
                logger.warning("[REDEPLOY] CLI may not be installed in container")

                # Пробуем установить CLI
                logger.info("[REDEPLOY] Attempting to install Railway CLI...")
                try:
                    install_result = subprocess.run(
                        ["curl", "-fsSL", "https://railway.app/install.sh"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        shell=True
                    )

                    if install_result.returncode == 0:
                        logger.info("[REDEPLOY] ✅ Railway CLI installed successfully")
                        logger.info(f"[REDEPLOY] Install output: {install_result.stdout[:200]}...")
                    else:
                        logger.error(f"[REDEPLOY] ❌ CLI installation failed: {install_result.stderr}")
                        return self._emergency_redeploy()
                except Exception as e:
                    logger.error(f"[REDEPLOY] ❌ CLI installation error: {e}")
                    return self._emergency_redeploy()

            # Попытка выполнить редеплой через CLI
            logger.info("[REDEPLOY] Executing: railway redeploy -y")
            result = subprocess.run(
                ["railway", "redeploy", "-y"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.getcwd()
            )

            logger.info(f"[REDEPLOY] CLI command result: return_code={result.returncode}")
            logger.info(f"[REDEPLOY] CLI stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"[REDEPLOY] CLI stderr: {result.stderr}")

            if result.returncode == 0:
                logger.info("[REDEPLOY] ════════════════════════════════════════")
                logger.info("[REDEPLOY] ✅ Railway redeploy via CLI successful!")
                logger.info("[REDEPLOY] 🔄 Service will restart gracefully (NO CRASH)")
                logger.info("[REDEPLOY] ⏱️  Expected downtime: ~30-60 seconds")
                logger.info("[REDEPLOY] ════════════════════════════════════════")

                self.last_redeploy_time = datetime.now(timezone(timedelta(hours=3)))
                self._save_last_redeploy_time(self.last_redeploy_time)
                self._reset_error_tracking()

                # Показать статус в Web UI
                logger.info(f"[REDEPLOY] 💡 Check Railway dashboard for deployment status")
                return True
            else:
                logger.error(f"[REDEPLOY] ❌ CLI redeploy failed with code {result.returncode}")
                logger.error(f"[REDEPLOY] Error output: {result.stderr}")

                # Попытка альтернативного метода через HTTP API
                logger.info("[REDEPLOY] 🔄 Trying HTTP API fallback...")
                return self._http_api_redeploy()

        except subprocess.TimeoutExpired:
            logger.error("[REDEPLOY] ❌ CLI redeploy timed out after 60 seconds")
            return self._emergency_redeploy()
        except FileNotFoundError:
            logger.error("[REDEPLOY] ❌ Railway CLI not found even after installation attempt")
            return self._emergency_redeploy()
        except Exception as e:
            logger.error(f"[REDEPLOY] ❌ Fallback redeploy failed: {e}")
            import traceback
            logger.error(f"[REDEPLOY] Traceback: {traceback.format_exc()}")
            return self._emergency_redeploy()
    
    def _emergency_redeploy(self):
        """Экстренный метод редеплоя через webhook или прямой триггер"""
        try:
            # КРИТИЧЕСКИ ВАЖНАЯ ИНФОРМАЦИЯ ПЕРЕД EMERGENCY
            total_errors = self.error_403_count + self.error_401_count + self.error_429_count
            
            logger.critical("[REDEPLOY] ════════════════════════════════════════")
            logger.critical("[REDEPLOY] 🚨 EMERGENCY REDEPLOY METHOD ACTIVATED")
            logger.critical("[REDEPLOY] ════════════════════════════════════════")
            logger.critical("[REDEPLOY] CURRENT ERROR STATE:")
            logger.critical(f"[REDEPLOY] - 403 errors: {self.error_403_count}")
            logger.critical(f"[REDEPLOY] - 401 errors: {self.error_401_count}")
            logger.critical(f"[REDEPLOY] - 429 errors: {self.error_429_count}")
            logger.critical(f"[REDEPLOY] - TOTAL: {total_errors}")
            logger.critical(f"[REDEPLOY] - Success streak: {self.success_streak}")
            logger.critical("[REDEPLOY] ════════════════════════════════════════")
            logger.critical("[REDEPLOY] Reason: Railway API and CLI methods failed")
            logger.critical("[REDEPLOY] ════════════════════════════════════════")
            
            # Обновляем время редеплоя
            self.last_redeploy_time = datetime.now(timezone(timedelta(hours=3)))
            logger.info(f"[REDEPLOY] Recording redeploy time: {self.last_redeploy_time}")
            self._save_last_redeploy_time(self.last_redeploy_time)
            self._reset_error_tracking()
            logger.info("[REDEPLOY] Error tracking reset")
            
            # Метод 1: Пробуем через Railway webhook (если настроен)
            webhook_url = os.getenv('RAILWAY_REDEPLOY_WEBHOOK')
            if webhook_url:
                try:
                    logger.info("[REDEPLOY] Attempting redeploy via webhook...")
                    response = requests.post(webhook_url, timeout=10)
                    if response.status_code in [200, 201, 202]:
                        logger.info("[REDEPLOY] ✅ Webhook redeploy successful!")
                        return True
                except Exception as e:
                    logger.warning(f"[REDEPLOY] Webhook failed: {e}")

            # Метод 2: LAST RESORT - принудительный выход (Railway перезапустит контейнер)
            # По умолчанию ВКЛЮЧЕН (как в старой версии cf7b0fb)
            # Можно отключить через ALLOW_EMERGENCY_EXIT=false
            allow_exit = os.getenv('ALLOW_EMERGENCY_EXIT', 'true').lower() == 'true'
            
            if allow_exit:
                logger.critical("[REDEPLOY] ════════════════════════════════════════")
                logger.critical("[REDEPLOY] 💣 METHOD 2: EMERGENCY EXIT (os._exit)")
                logger.critical("[REDEPLOY] 🔄 Forcing app restart - Railway will auto-restart")
                logger.critical("[REDEPLOY] ⏱️  Expected restart time: ~10-30 seconds")
                logger.critical("[REDEPLOY] ════════════════════════════════════════")
                
                # Даем время на запись логов и БД
                import threading
                def delayed_exit():
                    time.sleep(3)
                    logger.critical("[REDEPLOY] 💥 FORCING EXIT NOW...")
                    # КАК В СТАРОЙ ВЕРСИИ cf7b0fb: os._exit(1)
                    # Railway автоматически перезапустит контейнер
                    os._exit(1)
                
                thread = threading.Thread(target=delayed_exit)
                thread.daemon = True
                thread.start()
                
                return True
            else:
                # ⚠️ НЕ КРАШИМ БОТ!
                # Вместо краша просто сбрасываем счетчики и продолжаем работу
                logger.critical("[REDEPLOY] ════════════════════════════════════════")
                logger.critical("[REDEPLOY] ⚠️  All redeploy methods failed")
                logger.critical("[REDEPLOY] ✅ Error counters RESET - bot continues working")
                logger.critical("[REDEPLOY] 💡 To enable emergency exit, set: ALLOW_EMERGENCY_EXIT=true")
                logger.critical("[REDEPLOY] Note: Set RAILWAY_REDEPLOY_WEBHOOK env var for auto-redeploy")
                logger.critical("[REDEPLOY] Manual redeploy may be required if errors persist")
                logger.critical("[REDEPLOY] ════════════════════════════════════════")
                
                return False
            
        except Exception as e:
            logger.error(f"[REDEPLOY] Emergency redeploy failed: {e}")
            return False

    def _http_api_redeploy(self):
        """Альтернативный метод редеплоя через HTTP API"""
        try:
            logger.info("[REDEPLOY] 🌐 Trying HTTP API redeploy as last resort...")

            # Railway REST API для редеплоя
            url = f"https://backboard.railway.com/projects/{self.project_id}/services/{self.service_id}/redeploy"

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "RailwayRedeployManager/1.0"
            }

            logger.info(f"[REDEPLOY] HTTP API URL: {url}")
            logger.info(f"[REDEPLOY] Making POST request to trigger redeploy...")

            response = requests.post(url, headers=headers, timeout=30)

            logger.info(f"[REDEPLOY] HTTP API response status: {response.status_code}")
            logger.info(f"[REDEPLOY] HTTP API response: {response.text[:300]}...")

            if response.status_code in [200, 201, 202]:
                logger.info("[REDEPLOY] ════════════════════════════════════════")
                logger.info("[REDEPLOY] ✅ Railway HTTP API redeploy successful!")
                logger.info("[REDEPLOY] 🔄 Service will restart gracefully (NO CRASH)")
                logger.info("[REDEPLOY] ⏱️  Expected downtime: ~30-60 seconds")
                logger.info("[REDEPLOY] ════════════════════════════════════════")

                self.last_redeploy_time = datetime.now(timezone(timedelta(hours=3)))
                self._save_last_redeploy_time(self.last_redeploy_time)
                self._reset_error_tracking()

                logger.info(f"[REDEPLOY] 💡 Check Railway dashboard for deployment status")
                return True
            else:
                logger.error(f"[REDEPLOY] ❌ HTTP API redeploy failed: {response.status_code}")
                logger.error(f"[REDEPLOY] Response: {response.text}")
                return self._emergency_redeploy()

        except Exception as e:
            logger.error(f"[REDEPLOY] ❌ HTTP API redeploy failed: {e}")
            import traceback
            logger.error(f"[REDEPLOY] Traceback: {traceback.format_exc()}")
            return self._emergency_redeploy()
    
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
            current_time = datetime.now(timezone(timedelta(hours=3)))
            
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
                "success_streak": self.success_streak,
                "success_threshold": self.success_threshold,
                "last_redeploy_time": self.last_redeploy_time.isoformat() if self.last_redeploy_time else None,
                "redeploy_threshold_minutes": self.redeploy_threshold_minutes,
                "max_http_errors": self.max_http_errors
            }
            
            if first_error_time:
                time_since_first = current_time - first_error_time
                status["time_since_first_error_seconds"] = time_since_first.total_seconds()
                
                # Проверяем ОБА условия: обычное И критическое
                normal_condition = (
                    time_since_first.total_seconds() >= self.redeploy_threshold_minutes * 60 and
                    total_errors >= self.max_http_errors
                )
                critical_condition = total_errors >= 100
                
                status["redeploy_needed"] = normal_condition or critical_condition
                status["redeploy_reason"] = "critical" if critical_condition else ("normal" if normal_condition else "none")
            
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