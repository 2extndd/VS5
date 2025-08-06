#!/usr/bin/env python3
"""
Конфигурация для Railway API
"""
import os
from logger import get_logger

logger = get_logger(__name__)

def setup_railway_environment():
    """Настройка переменных окружения для Railway API"""
    
    # Проект ID - известный из команды railway link
    project_id = "101cc62f-b314-41d1-9b55-d58ae5c371ea"
    os.environ.setdefault('RAILWAY_PROJECT_ID', project_id)
    
    # Попытка получить токен из различных источников
    railway_token = None
    
    # 1. Из переменной окружения
    railway_token = os.getenv('RAILWAY_TOKEN')
    
    # 2. Из файла конфигурации Railway CLI (если доступен)
    if not railway_token:
        try:
            import json
            import pathlib
            
            # Путь к конфигурации Railway CLI
            config_path = pathlib.Path.home() / '.railway' / 'config.json'
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    railway_token = config.get('token')
                    if railway_token:
                        logger.info("[RAILWAY] Token loaded from Railway CLI config")
        except Exception as e:
            logger.debug(f"[RAILWAY] Could not load token from CLI config: {e}")
    
    # 3. Из Railway CLI команды (если доступен)
    if not railway_token:
        try:
            import subprocess
            
            result = subprocess.run(
                ['railway', 'whoami', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                # Токен обычно сохранен в CLI, попробуем получить его через auth
                logger.info("[RAILWAY] Railway CLI is authenticated")
                
                # Попробуем получить токен через переменные окружения Railway
                result_env = subprocess.run(
                    ['railway', 'run', 'env'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result_env.returncode == 0:
                    for line in result_env.stdout.split('\n'):
                        if 'RAILWAY_TOKEN' in line:
                            railway_token = line.split('=', 1)[1].strip()
                            break
                        
        except Exception as e:
            logger.debug(f"[RAILWAY] Could not get token from CLI: {e}")
    
    if railway_token:
        os.environ['RAILWAY_TOKEN'] = railway_token
        logger.info("[RAILWAY] Railway API token configured")
        return True
    else:
        logger.warning("[RAILWAY] Railway API token not found. Auto-redeploy will use fallback method.")
        return False

def get_service_id_from_cli():
    """Получить Service ID из Railway CLI"""
    try:
        import subprocess
        import json
        
        # Получаем информацию о текущем проекте
        result = subprocess.run(
            ['railway', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            service_id = data.get('serviceId')
            if service_id:
                os.environ['RAILWAY_SERVICE_ID'] = service_id
                logger.info(f"[RAILWAY] Service ID configured: {service_id}")
                return service_id
                
    except Exception as e:
        logger.debug(f"[RAILWAY] Could not get service ID from CLI: {e}")
    
    return None

# Автоматическая настройка при импорте
if __name__ != "__main__":
    setup_railway_environment()
    get_service_id_from_cli()