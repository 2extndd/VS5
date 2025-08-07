from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import db, core, os, re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from logger import get_logger
import configuration_values

# Импорт системы автоматического редеплоя
try:
    from railway_redeploy import get_redeploy_status
    REDEPLOY_MONITORING_AVAILABLE = True
except ImportError:
    REDEPLOY_MONITORING_AVAILABLE = False
    def get_redeploy_status():
        return {"error": "Railway redeploy system not available"}

# Get logger for this module
logger = get_logger(__name__)

# Create Flask app
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

# Secret key for session management
app.secret_key = os.urandom(24)


@app.context_processor
def inject_version_info():
    is_up_to_date, current_ver, latest_version, github_url = core.check_version()
    return {
        'github_url': github_url,
        'current_version': current_ver,
        'latest_version': latest_version,
        'is_up_to_date': is_up_to_date
    }


@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}


@app.route('/fix_settings')
def fix_settings():
    """Автоматическое исправление настроек для работы бота"""
    try:
        # Устанавливаем критические параметры
        updates = {
            'enable_logging': 'True',
            'query_refresh_delay': '300',  # 5 минут
            'max_retries': '3',
            'request_timeout': '30',
            'items_per_query': '2'
        }
        
        results = []
        for key, value in updates.items():
            try:
                db.set_parameter(key, value)
                results.append(f"✅ {key} = {value}")
            except Exception as e:
                results.append(f"❌ {key}: {e}")
        
        return jsonify({
            'status': 'success',
            'message': 'Настройки обновлены!',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка: {e}'
        })

@app.route('/diagnose')
def diagnose():
    """Диагностика состояния системы"""
    try:
        import sys
        import os
        import psutil
        import subprocess
        
        info = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'working_directory': os.getcwd(),
            'environment_vars': {
                'DATABASE_URL': 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET',
                'PORT': os.environ.get('PORT', 'NOT SET')
            },
            'database_params': {},
            'processes': [],
            'files_exist': {},
            'scheduler_status': 'UNKNOWN'
        }
        
        # Проверяем параметры базы
        try:
            params = db.get_all_parameters()
            info['database_params'] = params
        except Exception as e:
            info['database_params'] = {'error': str(e)}
        
        # Проверяем процессы
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'python' in proc.info['name'].lower():
                    info['processes'].append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    })
        except Exception as e:
            info['processes'] = [{'error': str(e)}]
        
        # Проверяем файлы
        files_to_check = [
            'vinted_notifications.py',
            'core.py',
            'db.py',
            'pyVintedVN/vinted.py'
        ]
        
        for file_path in files_to_check:
            info['files_exist'][file_path] = os.path.exists(file_path)
        
        # Пытаемся запустить основной процесс принудительно
        try:
            import threading
            import queue
            
            # Создаем очередь для тестирования
            test_queue = queue.Queue()
            
            # Импортируем и тестируем core
            sys.path.append('/app')  # Railway путь
            sys.path.append('.')
            
            try:
                import core
                info['core_import'] = 'SUCCESS'
                
                # Пытаемся запустить process_items в отдельном потоке
                def test_process():
                    try:
                        core.process_items(test_queue)
                        return 'SUCCESS'
                    except Exception as e:
                        return f'ERROR: {e}'
                
                # Не запускаем процесс, только проверяем импорт
                info['scheduler_status'] = 'READY TO START'
                
            except Exception as e:
                info['core_import'] = f'ERROR: {e}'
                
        except Exception as e:
            info['scheduler_status'] = f'ERROR: {e}'
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/force_start')
def force_start():
    """Принудительный запуск процесса сканирования"""
    try:
        import sys
        import os
        import threading
        import queue
        
        # Добавляем пути
        sys.path.append('/app')
        sys.path.append('.')
        
        # Тестируем импорт
        try:
            import core
            logger.info("✅ Core импортирован успешно")
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Ошибка импорта core: {e}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Создаем тестовую очередь
        test_queue = queue.Queue()
        
        # Тестируем запуск process_items
        def test_run():
            try:
                logger.info("🚀 Тестовый запуск process_items...")
                
                # Прямой тест поиска вещей БЕЗ ОЧЕРЕДИ
                import db
                all_queries = db.get_queries()
                logger.info(f"Found {len(all_queries)} queries in database")
                
                if len(all_queries) == 0:
                    return "ERROR: No queries in database"
                
                # Тестируем первый запрос
                from pyVintedVN.vinted import Vinted
                vinted = Vinted()
                
                first_query = all_queries[0]
                logger.info(f"Testing query: {first_query[1][:50]}...")
                
                try:
                    items = vinted.items.search(first_query[1], nbr_items=2)
                    logger.info(f"Search returned {len(items)} items")
                    
                    if len(items) > 0:
                        first_item = items[0]
                        logger.info(f"First item: {first_item.title} - {first_item.price}")
                        
                        # Пытаемся сохранить в базу напрямую
                        db.add_item_to_db(
                            id=first_item.id,
                            title=first_item.title,
                            query_id=first_query[0],
                            price=first_item.price,
                            timestamp=first_item.raw_timestamp,
                            photo_url=first_item.photo,
                            currency=first_item.currency
                        )
                        
                        # КРИТИЧНО: Обновляем статистику запроса!
                        db.update_query_last_found(first_query[0], first_item.raw_timestamp)
                        logger.info(f"Updated last_found for query {first_query[0]}")
                        
                        return f"SUCCESS: Found {len(items)} items, saved first item: {first_item.title}, updated statistics"
                    else:
                        return "SUCCESS: No items found in search"
                        
                except Exception as search_error:
                    import traceback
                    return f"SEARCH_ERROR: {search_error}\\n{traceback.format_exc()}"
                
            except Exception as e:
                import traceback
                return f"ERROR: {e}\\n{traceback.format_exc()}"
        
        # Запускаем в потоке с таймаутом
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(test_run)
            try:
                result = future.result(timeout=30)  # 30 секунд таймаут
                
                return jsonify({
                    'status': 'success',
                    'message': 'Process_items executed successfully',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except concurrent.futures.TimeoutError:
                return jsonify({
                    'status': 'timeout',
                    'message': 'Process_items execution timed out after 30 seconds',
                    'timestamp': datetime.now().isoformat()
                })
        
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': f'Force start error: {e}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/')
def index():
    # Get parameters
    params = db.get_all_parameters()

    # Queries section removed from dashboard

    # Get recent items (increased limit to 42)
    items = db.get_items(limit=42)
    formatted_items = []
    for item in items:
        try:
            # Safe timestamp conversion
            try:
                if item[4]:
                    timestamp_val = float(item[4])  # Convert Decimal to float
                    timestamp_str = datetime.fromtimestamp(timestamp_val).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp_str = 'Unknown'
            except (ValueError, TypeError, OSError):
                timestamp_str = 'Invalid timestamp'
            
            formatted_items.append({
                'id': str(item[0]) if item[0] else 'Unknown',
                'title': str(item[1]) if item[1] else 'Unknown title',
                'price': float(item[2]) if item[2] is not None else 0.0,
                'currency': str(item[3]) if item[3] else 'EUR',
                'timestamp': timestamp_str,
                'query': str(item[5]) if item[5] else 'Unknown query',
                'photo_url': str(item[6]) if item[6] else '',
                'brand_title': str(item[7]) if len(item) > 7 and item[7] else ''
            })
        except Exception as e:
            # Log the error and skip this item
            logger.error(f"Error formatting item {item}: {e}")
            continue

    # Get process status from the database
    telegram_running = db.get_parameter('telegram_process_running') == 'True'
    # RSS functionality removed

    # Get statistics for the dashboard
    stats = {
        'total_items': db.get_total_items_count(),
        'total_queries': db.get_total_queries_count(),
        'api_requests': db.get_api_requests_count(),
        'bot_uptime': db.get_bot_uptime()
    }

    # Get the last found item
    last_item = db.get_last_found_item()
    if last_item:
        try:
            # Safe timestamp conversion for last item
            try:
                if last_item[4]:
                    timestamp_val = float(last_item[4])  # Convert Decimal to float
                    last_timestamp_str = datetime.fromtimestamp(timestamp_val).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    last_timestamp_str = 'Unknown'
            except (ValueError, TypeError, OSError):
                last_timestamp_str = 'Invalid timestamp'
                
            stats['last_item'] = {
                'id': str(last_item[0]) if last_item[0] else 'Unknown',
                'title': str(last_item[1]) if last_item[1] else 'Unknown title',
                'price': float(last_item[2]) if last_item[2] is not None else 0.0,
                'currency': str(last_item[3]) if last_item[3] else 'EUR',
                'timestamp': last_timestamp_str,
                'query': str(last_item[5]) if last_item[5] else 'Unknown query',
                'photo_url': str(last_item[6]) if last_item[6] else ''
            }
        except Exception as e:
            logger.error(f"Error formatting last item {last_item}: {e}")
            stats['last_item'] = None
    else:
        stats['last_item'] = None

    return render_template('index.html',
                           params=params,
                           items=formatted_items,
                           telegram_running=telegram_running,
                           # RSS removed
                           stats=stats)


@app.route('/queries')
def queries():
    # Get queries
    all_queries = db.get_queries()
    formatted_queries = []
    for i, query in enumerate(all_queries):
        parsed_query = urlparse(query[1])
        query_params = parse_qs(parsed_query.query)
        query_name = query[3] if query[3] is not None else query_params.get('search_text', [None])[0]

        # Get the last timestamp for this query
        try:
            last_timestamp = db.get_last_timestamp(query[0])
            if last_timestamp:
                # Convert Decimal to float for PostgreSQL compatibility
                timestamp_float = float(last_timestamp)
                last_found_item = datetime.fromtimestamp(timestamp_float).strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_found_item = "Never"
        except Exception as e:
            logger.warning(f"Error formatting timestamp: {e}")
            last_found_item = "Never"

        # Get thread_id (5th element, index 4) if available
        thread_id = None
        if len(query) > 4:
            thread_id = query[4]
            
        # Get items count for this query
        items_count = db.get_items_count_by_query(query[0])
            
        formatted_queries.append({
            'id': i + 1,
            'query_id': query[0],  # ID для ссылок на /items
            'query': query[1],     # URL Vinted для внешних ссылок
            'display': query_name if query_name else query[1],
            'last_found_item': last_found_item,
            'thread_id': thread_id,
            'items_count': items_count
        })

    # Sort by thread_id AND query name within each thread group
    def sort_key(q):
        thread_id = q['thread_id']
        query_name = q['display']
        
        # Primary sort: thread_id
        if thread_id is None or thread_id == '':
            thread_priority = (0, 0)
        else:
            try:
                thread_priority = (1, int(thread_id))
            except (ValueError, TypeError):
                thread_priority = (2, str(thread_id))
        
        # Secondary sort: query name (natural sort for numbers)
        import re
        # Extract numbers from query name for natural sorting (D&G 1, D&G 2, D&G 3)
        name_parts = re.findall(r'(\D+)(\d*)', query_name)
        if name_parts:
            text_part = name_parts[0][0].strip()
            num_part = int(name_parts[0][1]) if name_parts[0][1] else 0
            name_priority = (text_part, num_part)
        else:
            name_priority = (query_name, 0)
        
        return (thread_priority, name_priority)

    formatted_queries.sort(key=sort_key)
    
    # Re-assign sequential IDs after sorting
    for i, query in enumerate(formatted_queries):
        query['id'] = i + 1

    return render_template('queries.html', queries=formatted_queries)


@app.route('/add_query', methods=['POST'])
def add_query():
    query = request.form.get('query')
    query_name = request.form.get('query_name', '').strip()
    thread_id = request.form.get('thread_id', '').strip()
    
    if query:
        # Convert thread_id to integer if provided
        thread_id_int = None
        if thread_id:
            try:
                thread_id_int = int(thread_id)
            except ValueError:
                flash('Invalid thread ID. Must be a number.', 'error')
                return redirect(url_for('queries'))
        
        message, is_new_query = core.process_query(query, name=query_name if query_name != '' else None, thread_id=thread_id_int)
        
        if is_new_query:
            flash(f'Query added: {query}', 'success')
        else:
            flash(message, 'warning')
    else:
        flash('No query provided', 'error')

    return redirect(url_for('queries'))


@app.route('/update_thread_id', methods=['POST'])
def update_thread_id():
    query_id = request.form.get('query_id')
    thread_id = request.form.get('thread_id', '').strip()
    
    if query_id:
        # Convert thread_id to integer if provided, None if empty
        thread_id_int = None
        if thread_id:
            try:
                thread_id_int = int(thread_id)
            except ValueError:
                flash('Invalid thread ID. Must be a number.', 'error')
                return redirect(url_for('queries'))
        
        # Find the actual database ID for this query
        all_queries = db.get_queries()
        db_query_id = None
        for q in all_queries:
            if str(q[0]) == query_id:  # Compare string representations
                db_query_id = q[0]
                break
        
        if db_query_id:
            success = db.update_query_thread_id(db_query_id, thread_id_int)
            if success:
                if thread_id_int:
                    flash(f'Thread ID updated to {thread_id_int}', 'success')
                else:
                    flash('Thread ID cleared', 'success')
            else:
                flash('Failed to update thread ID', 'error')
        else:
            flash('Query not found', 'error')
    else:
        flash('No query ID provided', 'error')

    return redirect(url_for('queries'))


@app.route('/remove_query/<int:query_id>', methods=['POST'])
def remove_query(query_id):
    message, success = core.process_remove_query(str(query_id))
    if success:
        flash('Query removed', 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('queries'))


@app.route('/clear_all_items', methods=['POST'])
def clear_all_items():
    """Clear all items from the database and reset query timestamps"""
    success = db.clear_all_items()
    if success:
        flash('All items cleared successfully. Bot will rescan all queries and resend items to Telegram.', 'success')
        logger.info("All items cleared from database via web interface")
    else:
        flash('Failed to clear items. Please try again.', 'error')
        logger.error("Failed to clear items from database via web interface")
    
    return redirect(url_for('index'))


@app.route('/edit_query/<int:query_id>', methods=['POST'])
def edit_query(query_id):
    """Edit an existing query"""
    try:
        new_query = request.form.get('query', '').strip()
        new_name = request.form.get('query_name', '').strip()
        
        if not new_query:
            flash('Query URL is required', 'error')
            return redirect(url_for('queries'))
        
        # Get existing query
        queries = db.get_queries()
        existing_query = None
        for q in queries:
            if q[0] == query_id:
                existing_query = q
                break
                
        if not existing_query:
            flash('Query not found', 'error')
            return redirect(url_for('queries'))
        
        # Update query in database
        conn, db_type = db.get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgresql':
            cursor.execute("""
                UPDATE queries 
                SET query = %s, query_name = %s 
                WHERE id = %s
            """, (new_query, new_name if new_name else None, query_id))
        else:
            cursor.execute(
                "UPDATE queries SET query = ?, query_name = ? WHERE id = ?",
                (new_query, new_name if new_name else None, query_id))
        
        conn.commit()
        conn.close()
        
        flash(f'Query "{new_name or new_query}" updated successfully', 'success')
        logger.info(f"Query {query_id} updated: {new_query}")
        
    except Exception as e:
        logger.error(f"Error editing query {query_id}: {e}")
        flash(f'Error updating query: {e}', 'error')
    
    return redirect(url_for('queries'))


@app.route('/remove_query/all', methods=['POST'])
def remove_all_queries():
    message, success = core.process_remove_query("all")
    if success:
        flash('All queries removed', 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('queries'))


@app.route('/items')
def items():
    query_id = request.args.get('query', '')  # Default to empty string instead of None
    limit = int(request.args.get('limit', 50))

    # Get items
    query_string = None
    if query_id:
        # Get the actual query string for the given ID
        queries = db.get_queries()
        for q in queries:
            if str(q[0]) == query_id:
                query_string = q[1]
                break

    # If limit is 0, get all items (no limit)
    items_limit = None if limit == 0 else limit
    items_data = db.get_items(limit=items_limit, query=query_string)
    formatted_items = []

    for item in items_data:
        try:
            # Safe timestamp conversion
            try:
                if item[4]:
                    timestamp_val = float(item[4])  # Convert Decimal to float
                    timestamp_str = datetime.fromtimestamp(timestamp_val).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp_str = 'Unknown'
            except (ValueError, TypeError, OSError):
                timestamp_str = 'Invalid timestamp'
            
            # Safe query parsing
            try:
                if item[5]:
                    parsed_query = urlparse(item[5])
                    query_params = parse_qs(parsed_query.query)
                    search_text = query_params.get('search_text', [None])[0]
                    query_display = search_text if search_text else item[5]
                else:
                    query_display = 'Unknown query'
            except:
                query_display = str(item[5]) if item[5] else 'Unknown query'
            
            # Check if item is recent (last 24 hours)
            is_recent = False
            try:
                if item[4]:
                    timestamp_val = float(item[4])
                    import time
                    current_time = time.time()
                    hours_ago = (current_time - timestamp_val) / 3600
                    is_recent = hours_ago < 24
            except:
                is_recent = False
            
            formatted_items.append({
                'title': str(item[1]) if item[1] else 'Unknown title',
                'price': float(item[2]) if item[2] is not None else 0.0,
                'currency': str(item[3]) if item[3] else 'EUR',
                'timestamp': timestamp_str,
                'query': query_display,
                'url': f'https://www.vinted.de/items/{item[0]}',
                'photo_url': str(item[6]) if item[6] else '',
                'brand_title': str(item[7]) if len(item) > 7 and item[7] else '',
                'is_recent': is_recent
            })
        except Exception as e:
            # Log the error and skip this item
            from logger import get_logger
            logger = get_logger(__name__)
            logger.error(f"Error formatting item {item}: {e}")
            continue

    # Get queries for filter dropdown
    queries = db.get_queries()
    formatted_queries = []
    selected_query_display = None
    for i, q in enumerate(queries):
        parsed_query = urlparse(q[1])
        query_params = parse_qs(parsed_query.query)
        query_name = q[3] if q[3] is not None else query_params.get('search_text', [None])[0]
        display_name = query_name if query_name else q[0]
        # Store display name for selected query
        if query_id == str(q[0]):
            selected_query_display = display_name
        formatted_queries.append({
            'id': i + 1,
            'query': str(q[0]),  # Ensure query is a string
            'display': display_name
        })

    return render_template('items.html',
                           items=formatted_items,
                           queries=formatted_queries,
                           selected_query=query_id,
                           selected_query_display=selected_query_display,
                           limit=limit)


@app.route('/config')
def config():
    params = db.get_all_parameters()
    countries = db.get_allowlist()
    return render_template('config.html', params=params, countries=countries)


@app.route('/update_config', methods=['POST'])
def update_config():
    try:
        logger.info(f"[CONFIG] Update config request received")
        logger.info(f"[CONFIG] Form data: {dict(request.form)}")
        
        # Update Telegram parameters
        telegram_enabled = 'telegram_enabled' in request.form
        logger.info(f"[CONFIG] Telegram enabled: {telegram_enabled}")
        db.set_parameter('telegram_enabled', str(telegram_enabled))
        db.set_parameter('telegram_token', request.form.get('telegram_token', ''))
        db.set_parameter('telegram_chat_id', request.form.get('telegram_chat_id', ''))

        # RSS parameters removed

        # Update System parameters
        items_per_query = request.form.get('items_per_query', '20')
        query_refresh_delay = request.form.get('query_refresh_delay', '60')
        logger.info(f"[CONFIG] System params - items_per_query: {items_per_query}, query_refresh_delay: {query_refresh_delay}")
        db.set_parameter('items_per_query', items_per_query)
        db.set_parameter('query_refresh_delay', query_refresh_delay)

        # Update Proxy parameters
        check_proxies = 'check_proxies' in request.form
        logger.info(f"[CONFIG] Check proxies: {check_proxies}")
        db.set_parameter('check_proxies', str(check_proxies))
        db.set_parameter('proxy_list', request.form.get('proxy_list', ''))
        db.set_parameter('proxy_list_link', request.form.get('proxy_list_link', ''))

        # Reset proxy cache to force refresh on next use
        db.set_parameter('last_proxy_check_time', "1")
        logger.info("Proxy settings updated, cache reset")

        logger.info("[CONFIG] Configuration update completed successfully")
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('config'))
        
    except Exception as e:
        logger.error(f"[CONFIG] Error updating configuration: {e}")
        logger.error(f"[CONFIG] Full traceback:", exc_info=True)
        flash(f'Error updating configuration: {str(e)}', 'error')
        return redirect(url_for('config'))


@app.route('/test_config', methods=['GET', 'POST'])
def test_config():
    """Test endpoint for configuration debugging"""
    if request.method == 'GET':
        return jsonify({
            'status': 'ok',
            'message': 'Config endpoint is accessible',
            'method': 'GET'
        })
    else:
        return jsonify({
            'status': 'ok',
            'message': 'Config endpoint received POST request',
            'form_data': dict(request.form),
            'method': 'POST'
        })


@app.route('/control/<process_name>/<action>', methods=['POST'])
def control_process(process_name, action):
    if process_name not in ['telegram']:
        return jsonify({'status': 'error', 'message': 'Invalid process name'})

    if action == 'start':
        if process_name == 'telegram':
            # Check current status
            if db.get_parameter('telegram_process_running') == 'True':
                return jsonify({'status': 'warning', 'message': 'Telegram bot already running'})

            # Check if telegram_token and telegram_chat_id are set
            telegram_token = db.get_parameter('telegram_token')
            telegram_chat_id = db.get_parameter('telegram_chat_id')
            if not telegram_token or not telegram_chat_id:
                return jsonify({'status': 'error',
                                'message': 'Please set Telegram token and chat ID in the configuration panel before starting the Telegram process'})

            # Update process status in the database
            # The manager process will detect this and start the process
            db.set_parameter('telegram_process_running', 'True')
            logger.info("Telegram bot process start requested")
            return jsonify({'status': 'success', 'message': 'Telegram bot start requested'})

        # RSS process removed

    elif action == 'stop':
        if process_name == 'telegram':
            # Check current status
            if db.get_parameter('telegram_process_running') != 'True':
                return jsonify({'status': 'warning', 'message': 'Telegram bot not running'})

            # Update process status in the database
            # The manager process will detect this and stop the process
            db.set_parameter('telegram_process_running', 'False')
            logger.info("Telegram bot process stop requested")
            return jsonify({'status': 'success', 'message': 'Telegram bot stop requested'})

        # RSS process removed

    return jsonify({'status': 'error', 'message': 'Invalid action'})


@app.route('/control/status', methods=['GET'])
def process_status():
    # Get process status from the database
    telegram_running = db.get_parameter('telegram_process_running') == 'True'
    # RSS removed

    return jsonify({
        'telegram': telegram_running
    })


@app.route('/allowlist')
def allowlist():
    countries = db.get_allowlist()
    if countries == 0:
        countries = []

    return render_template('allowlist.html', countries=countries)


@app.route('/add_country', methods=['POST'])
def add_country():
    country = request.form.get('country', '').strip()
    if country:
        message, country_list = core.process_add_country(country)
        flash(message, 'success' if 'added' in message else 'warning')
    else:
        flash('No country provided', 'error')

    return redirect(url_for('config'))


@app.route('/remove_country/<country>', methods=['POST'])
def remove_country(country):
    message, country_list = core.process_remove_country(country)
    flash(message, 'success')

    return redirect(url_for('config'))


@app.route('/clear_allowlist', methods=['POST'])
def clear_allowlist():
    db.clear_allowlist()
    flash('Allowlist cleared', 'success')

    return redirect(url_for('config'))


@app.route('/logs')
def logs():
    return render_template('logs.html')


@app.route('/api/logs')
def api_logs():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 100))
    level_filter = request.args.get('level', 'all')

    log_file_path = os.path.join('logs', 'vinted.log')

    if not os.path.exists(log_file_path):
        return jsonify({'logs': [], 'total': 0})

    # Parse log file
    log_entries = []
    total_matching_entries = 0

    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            # Read all lines from the file
            all_lines = file.readlines()

            # Process lines in reverse order (newest first)
            all_lines.reverse()

            # Regular expression to parse log lines
            # Format: 2023-09-15 12:34:56,789 - module_name - LEVEL - Message
            log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - ([A-Z]+) - (.+)'

            current_entry = 0

            for line in all_lines:
                match = re.match(log_pattern, line.strip())
                if match:
                    timestamp, module, level, message = match.groups()

                    # Apply level filter if specified
                    if level_filter != 'all' and level != level_filter:
                        continue

                    total_matching_entries += 1

                    # Skip entries before offset
                    if total_matching_entries <= offset:
                        continue

                    # Add entry if within limit
                    if current_entry < limit:
                        log_entries.append({
                            'timestamp': timestamp,
                            'module': module.strip(),
                            'level': level,
                            'message': message
                        })
                        current_entry += 1

                    # Stop if we've reached the limit
                    if current_entry >= limit:
                        break
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return jsonify({'logs': [], 'total': 0, 'error': str(e)})

    return jsonify({
        'logs': log_entries,
        'total': total_matching_entries
    })


@app.route('/start_schedulers')
def start_schedulers():
    """Manually start schedulers if they're not running"""
    try:
        import threading
        import time
        from apscheduler.schedulers.background import BackgroundScheduler
        
        # Get current parameters
        query_refresh_delay_param = db.get_parameter("query_refresh_delay")
        current_query_refresh_delay = int(query_refresh_delay_param) if query_refresh_delay_param else 30
        
        # Global schedulers (if they exist)
        global scraper_scheduler, processor_scheduler
        
        results = []
        
        # Check and start scraper scheduler
        try:
            if 'scraper_scheduler' not in globals() or not scraper_scheduler.running:
                scraper_scheduler = BackgroundScheduler()
                import core
                import queue
                
                # Create a queue for this scheduler
                items_queue = queue.Queue()
                
                scraper_scheduler.add_job(
                    core.process_items, 
                    'interval', 
                    seconds=current_query_refresh_delay,
                    args=[items_queue], 
                    name="scraper"
                )
                scraper_scheduler.start()
                results.append(f"✅ Scraper scheduler started ({current_query_refresh_delay}s)")
            else:
                results.append(f"✅ Scraper scheduler already running")
        except Exception as e:
            results.append(f"❌ Scraper scheduler error: {e}")
        
        # Check and start processor scheduler  
        try:
            if 'processor_scheduler' not in globals() or not processor_scheduler.running:
                processor_scheduler = BackgroundScheduler()
                
                new_items_queue = queue.Queue()
                
                processor_scheduler.add_job(
                    core.clear_item_queue,
                    'interval', 
                    seconds=1,
                    args=[items_queue, new_items_queue], 
                    name="item_processor"
                )
                processor_scheduler.start()
                results.append("✅ Processor scheduler started (1s)")
            else:
                results.append("✅ Processor scheduler already running")
        except Exception as e:
            results.append(f"❌ Processor scheduler error: {e}")
        
        return jsonify({
            'status': 'success',
            'message': 'Schedulers check completed',
            'results': results,
            'refresh_delay': current_query_refresh_delay
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Error starting schedulers: {e}'
        })


@app.route('/test_telegram')
def test_telegram():
    """Test Telegram sending manually"""
    try:
        # Test message
        test_content = "🧪 <b>ТЕСТ TELEGRAM БОТА</b>\n\nЭто тестовое сообщение для проверки работы бота.\n\n💰 Цена: ТЕСТ\n🔗 Ссылка: ТЕСТ"
        
        # Send test message using requests (async alternative)
        import requests
        
        token = db.get_parameter("telegram_token") 
        chat_id = db.get_parameter("telegram_chat_id")
        
        if not token or not chat_id:
            return jsonify({
                'status': 'error',
                'message': 'Telegram token or chat_id not configured'
            })
        
        # Send message via Telegram API
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': test_content,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return jsonify({
                    'status': 'success',
                    'message': 'Test message sent to Telegram successfully!',
                    'telegram_response': result
                })
            else:
                return jsonify({
                    'status': 'error', 
                    'message': f'Telegram API error: {result}'
                })
        else:
            return jsonify({
                'status': 'error',
                'message': f'HTTP error: {response.status_code}'
            })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error testing Telegram: {e}'
        })


@app.route('/force_telegram_bot')
def force_telegram_bot():
    """Force start simple Telegram sender"""
    try:
        import threading
        import queue
        import time
        
        def simple_telegram_sender():
            """Simple Telegram sender without polling"""
            try:
                logger.info("Starting simple Telegram sender...")
                
                # Get Telegram credentials
                token = db.get_parameter("telegram_token")
                chat_id = db.get_parameter("telegram_chat_id")
                
                if not token or not chat_id:
                    logger.error("Telegram credentials not found")
                    return
                
                # Create a queue and add test item
                import requests
                
                # Send test message
                test_content = "🚀 <b>ПРОСТОЙ TELEGRAM ОТПРАВЩИК РАБОТАЕТ!</b>\n\nЭто сообщение отправлено через упрощенный отправщик без polling."
                
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': test_content,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(url, data=data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        logger.info("✅ Test message sent to Telegram successfully!")
                    else:
                        logger.error(f"❌ Telegram API error: {result}")
                else:
                    logger.error(f"❌ HTTP error: {response.status_code}")
                
                # Now start monitoring for real items
                logger.info("Starting queue monitoring...")
                
                # Simulate queue processing (in real app this would be the actual queue)
                counter = 0
                while counter < 10:  # Run for 10 iterations as test
                    logger.info(f"[SIMPLE_TELEGRAM] Queue check #{counter + 1}")
                    
                    # Here we would check the actual new_items_queue
                    # For now, just log that we're monitoring
                    time.sleep(2)
                    counter += 1
                
                logger.info("Simple Telegram sender completed test run")
                
            except Exception as e:
                logger.error(f"Error in simple Telegram sender: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Start in thread
        telegram_thread = threading.Thread(target=simple_telegram_sender, daemon=True)
        telegram_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Simple Telegram sender started - check your Telegram chat!',
            'note': 'This bypasses the complex LeRobot polling system'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error starting simple Telegram sender: {e}'
        })


@app.route('/send_items_to_telegram')
def send_items_to_telegram():
    """Directly send found items to Telegram"""
    try:
        import requests as req
        
        # Get Telegram credentials
        token = db.get_parameter("telegram_token")
        chat_id = db.get_parameter("telegram_chat_id")
        
        if not token or not chat_id:
            return jsonify({
                'status': 'error',
                'message': 'Telegram credentials not configured'
            })
        
        # Get recent items from database
        try:
            conn, db_type = db.get_db_connection()
            cursor = conn.cursor()
            
            # Get last 3 items with thread_id
            if db_type == 'postgresql':
                cursor.execute("""
                    SELECT i.title, i.price, i.currency, q.query, i.timestamp, q.thread_id, q.query_name
                    FROM items i 
                    JOIN queries q ON i.query_id = q.id 
                    ORDER BY i.timestamp DESC 
                    LIMIT 3
                """)
            else:
                cursor.execute("""
                    SELECT i.title, i.price, i.currency, q.query, i.timestamp, q.thread_id, q.query_name
                    FROM items i 
                    JOIN queries q ON i.query_id = q.id 
                    ORDER BY i.timestamp DESC 
                    LIMIT 3
                """)
            
            items = cursor.fetchall()
            conn.close()
            
            if not items:
                return jsonify({
                    'status': 'warning',
                    'message': 'No items found in database'
                })
            
            # Send each item to Telegram
            sent_count = 0
            for item in items:
                title, price, currency, query_url, timestamp, thread_id, query_name = item
                
                # Create message content with query name if available
                query_display = query_name if query_name else query_url[:50] + "..."
                content = f"{title}\\n{price} {currency} (Size N/A)\\nN/A"
                
                # Send to Telegram with thread_id support
                api_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    'chat_id': chat_id,
                    'text': content,
                    'parse_mode': 'HTML'
                }
                
                # Add thread_id if specified
                if thread_id:
                    data['message_thread_id'] = int(thread_id)
                    logger.info(f"📍 Sending item to thread_id: {thread_id} ({query_display})")
                else:
                    logger.info(f"📍 Sending item to main chat ({query_display})")
                
                response = req.post(api_url, data=data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        sent_count += 1
                        logger.info(f"✅ Item sent to Telegram: {title}")
                    else:
                        logger.error(f"❌ Telegram API error for {title}: {result}")
                else:
                    logger.error(f"❌ HTTP error for {title}: {response.status_code}")
            
            return jsonify({
                'status': 'success',
                'message': f'Sent {sent_count}/{len(items)} items to Telegram',
                'sent_count': sent_count,
                'total_items': len(items)
            })
            
        except Exception as db_error:
            return jsonify({
                'status': 'error',
                'message': f'Database error: {db_error}'
            })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error sending items to Telegram: {e}'
        })


@app.route('/set_thread_ids')
def set_thread_ids():
    """Quick setup of thread_ids for queries"""
    try:
        # Thread mappings based on real query names from Railway
        thread_mappings = {
            'MM': '100',        # Для всех MM запросов (MM 1-7)
            'Prada': '200',     # Для всех Prada запросов (Prada 1-4)
            'D&G': '300',       # Для всех D&G запросов (D&G 1-4)
            'GGL': '400',       # Для GGL запроса
            'Rick Owens': '500', # Для Rick Owens запроса
        }
        
        # Get all queries
        queries = db.get_queries()
        updated_count = 0
        
        for query in queries:
            query_id, query_url, query_name = query[0], query[1], query[2] if len(query) > 2 else None
            
            # Find matching thread_id based on query name
            thread_id = None
            query_display = str(query_name or query_url)  # Convert to string for PostgreSQL Decimal
            
            for brand, tid in thread_mappings.items():
                if brand.lower() in query_display.lower():
                    thread_id = tid
                    break
            
            if thread_id:
                # Update thread_id for this query
                success = db.update_query_thread_id(query_id, thread_id)
                if success:
                    updated_count += 1
                    logger.info(f"✅ Updated thread_id for query {query_id} ({query_display}): {thread_id}")
                else:
                    logger.error(f"❌ Failed to update thread_id for query {query_id}")
        
        return jsonify({
            'status': 'success',
            'message': f'Updated thread_ids for {updated_count} queries',
            'updated_count': updated_count,
            'total_queries': len(queries),
            'mappings': thread_mappings,
            'note': 'Modify the thread_mappings in the code with your real thread_ids'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error setting thread_ids: {e}'
        })


@app.route('/force_scan_all', methods=['POST'])
def force_scan_all():
    """Force scan all queries immediately"""
    try:
        import threading
        from core import process_items
        import queue
        
        # Create queues for the scan
        items_queue = queue.Queue()
        new_items_queue = queue.Queue()
        
        logger.info("🚀 ПРИНУДИТЕЛЬНОЕ СКАНИРОВАНИЕ ВСЕХ ФИЛЬТРОВ ЗАПУЩЕНО!")
        
        # Run process_items in a thread to avoid blocking the web request
        def scan_thread():
            try:
                logger.info("Starting forced scan of all queries...")
                process_items(items_queue)
                logger.info("Forced scan completed!")
            except Exception as e:
                logger.error(f"Error in forced scan: {e}")
        
        # Start scan in background thread
        scan_thread_obj = threading.Thread(target=scan_thread, daemon=True)
        scan_thread_obj.start()
        
        # Get current stats for response
        queries = db.get_queries()
        query_count = len(queries)
        
        return jsonify({
            'status': 'success',
            'message': f'Force scan started for {query_count} queries',
            'queries_scanned': query_count,
            'note': 'Scan is running in background. Check dashboard in a few moments for updated results.'
        })
        
    except Exception as e:
        logger.error(f"Error in force_scan_all: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error starting force scan: {e}'
        })


@app.route('/system_analysis')
def system_analysis():
    """Analyze system performance and scanning frequency"""
    try:
        # Get current configuration
        query_refresh_delay = db.get_parameter("query_refresh_delay") or "30"
        items_per_query = db.get_parameter("items_per_query") or "20"
        
        # Get query count
        queries = db.get_queries()
        query_count = len(queries)
        
        # Calculate scanning frequency
        refresh_delay_seconds = int(query_refresh_delay)
        scans_per_minute = 60 / refresh_delay_seconds
        scans_per_hour = scans_per_minute * 60
        
        # Calculate Vinted API requests
        requests_per_scan = query_count  # One request per query per scan
        requests_per_hour = requests_per_scan * scans_per_hour
        
        # Estimate items processed
        items_per_scan = query_count * int(items_per_query)
        items_per_hour = items_per_scan * scans_per_hour
        
        # Get recent activity stats
        total_items = db.get_total_items_count()
        items_today = 0  # Removed old items_per_day calculation
        
        analysis = {
            'configuration': {
                'query_refresh_delay': f"{refresh_delay_seconds} seconds",
                'items_per_query': items_per_query,
                'total_queries': query_count
            },
            'scanning_frequency': {
                'scans_per_minute': round(scans_per_minute, 2),
                'scans_per_hour': round(scans_per_hour, 2),
                'scans_per_day': round(scans_per_hour * 24, 2)
            },
            'api_load': {
                'requests_per_scan': requests_per_scan,
                'requests_per_hour': round(requests_per_hour, 2),
                'requests_per_day': round(requests_per_hour * 24, 2)
            },
            'item_processing': {
                'items_per_scan_max': items_per_scan,
                'items_per_hour_max': round(items_per_hour, 2),
                'items_per_day_max': round(items_per_hour * 24, 2)
            },
            'actual_stats': {
                'total_items_found': total_items,
                'items_today': items_today,
                'average_items_per_query': round(total_items / query_count, 2) if query_count > 0 else 0
            },
            'recommendations': []
        }
        
        # Add recommendations based on analysis
        if requests_per_hour > 1000:
            analysis['recommendations'].append({
                'type': 'warning',
                'message': f'High API load: {requests_per_hour:.0f} requests/hour. Consider increasing refresh delay.'
            })
        
        if refresh_delay_seconds < 60:
            analysis['recommendations'].append({
                'type': 'info',
                'message': 'Fast scanning (< 1 minute). Good for real-time monitoring but increases API load.'
            })
        
        if query_count > 20:
            analysis['recommendations'].append({
                'type': 'warning',
                'message': f'Many queries ({query_count}). Consider consolidating similar searches.'
            })
        
        if not analysis['recommendations']:
            analysis['recommendations'].append({
                'type': 'success',
                'message': 'System configuration looks optimal!'
            })
        
        return jsonify({
            'status': 'success',
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Error in system_analysis: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error analyzing system: {e}'
        })


@app.route('/telegram_commands')
def telegram_commands():
    """List all supported Telegram bot commands"""
    try:
        commands = [
            {
                'command': '/hello',
                'description': 'Приветствие от бота',
                'usage': '/hello',
                'example': '/hello'
            },
            {
                'command': '/app',
                'description': 'Открыть веб-интерфейс приложения',
                'usage': '/app',
                'example': '/app'
            },
            {
                'command': '/add_query',
                'description': 'Добавить новый запрос для мониторинга',
                'usage': '/add_query [name=]<vinted_url>',
                'example': '/add_query https://www.vinted.de/catalog?brand_ids=212366\n/add_query MM 6=https://www.vinted.de/catalog?brand_ids=212366'
            },
            {
                'command': '/remove_query',
                'description': 'Удалить запрос по номеру (или все запросы)',
                'usage': '/remove_query <number|all>',
                'example': '/remove_query 1\n/remove_query all'
            },
            {
                'command': '/queries',
                'description': 'Показать все текущие запросы',
                'usage': '/queries',
                'example': '/queries'
            },
            {
                'command': '/allowlist',
                'description': 'Показать список разрешенных стран',
                'usage': '/allowlist',
                'example': '/allowlist'
            },
            {
                'command': '/clear_allowlist',
                'description': 'Очистить список разрешенных стран (разрешить все)',
                'usage': '/clear_allowlist',
                'example': '/clear_allowlist'
            },
            {
                'command': '/add_country',
                'description': 'Добавить страну в allowlist',
                'usage': '/add_country <country_code>',
                'example': '/add_country DE\n/add_country Germany'
            },
            {
                'command': '/remove_country',
                'description': 'Удалить страну из allowlist',
                'usage': '/remove_country <country_code>',
                'example': '/remove_country DE\n/remove_country Germany'
            }
        ]
        
        return jsonify({
            'status': 'success',
            'commands': commands,
            'total_commands': len(commands),
            'note': 'Все команды работают только в приватном чате с ботом или в группе где бот является администратором'
        })
        
    except Exception as e:
        logger.error(f"Error in telegram_commands: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting telegram commands: {e}'
        })


@app.route('/test_proxies')
def test_proxies():
    """Test all proxies and system integration"""
    import requests
    import time
    import concurrent.futures
    from proxies import get_random_proxy, convert_proxy_string_to_dict, convert_webshare_to_standard
    
    results = {
        "timestamp": time.time(),
        "proxy_system_test": {},
        "individual_tests": [],
        "summary": {}
    }
    
    try:
        # Test 1: get_random_proxy() function
        logger.info("Testing get_random_proxy() function...")
        start_time = time.time()
        random_proxy = get_random_proxy()
        proxy_fetch_time = time.time() - start_time
        
        results["proxy_system_test"] = {
            "proxy_returned": random_proxy is not None,
            "proxy_value": random_proxy,
            "fetch_time": proxy_fetch_time,
            "status": "OK" if random_proxy else "NO_PROXY"
        }
        
        # Test 2: Database proxy list
        proxy_list = db.get_parameter("proxy_list")
        if proxy_list:
            # Try to parse as list first
            try:
                import ast
                proxies = ast.literal_eval(proxy_list)
                proxy_source = "database_list"
            except:
                # Try newline parsing
                proxies_by_lines = [p.strip() for p in proxy_list.split('\n') if p.strip()]
                if len(proxies_by_lines) > 1:
                    proxies = proxies_by_lines
                    proxy_source = "newline_format"
                else:
                    proxies = [p.strip() for p in proxy_list.split(';') if p.strip()]
                    proxy_source = "semicolon_format"
        else:
            proxies = []
            proxy_source = "empty"
        
        # Test 3: Individual proxy testing (first 5)
        test_proxies = proxies[:5] if len(proxies) > 5 else proxies
        
        def test_single_proxy(proxy):
            try:
                # Check if WebShare format
                parts = proxy.strip().split(':')
                if len(parts) == 4 and not ('://' in proxy or '@' in proxy):
                    # Convert WebShare to standard
                    proxy = convert_webshare_to_standard(proxy)
                    proxy_type = "webshare_converted"
                else:
                    proxy_type = "standard"
                
                proxy_dict = convert_proxy_string_to_dict(proxy)
                ip = proxy.split('@')[1].split(':')[0] if '@' in proxy else proxy.split(':')[0]
                
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                start_time = time.time()
                response = session.get('https://httpbin.org/ip', proxies=proxy_dict, timeout=8)
                test_time = time.time() - start_time
                
                return {
                    "ip": ip,
                    "proxy_type": proxy_type,
                    "status": "OK",
                    "response_time": test_time,
                    "http_status": response.status_code,
                    "returned_ip": response.json().get('origin', 'unknown') if response.status_code == 200 else None
                }
                
            except Exception as e:
                parts = proxy.strip().split(':')
                ip = parts[0] if len(parts) >= 1 else 'unknown'
                return {
                    "ip": ip,
                    "proxy_type": "unknown",
                    "status": "ERROR",
                    "error": str(e)[:100],
                    "response_time": None
                }
        
        logger.info(f"Testing {len(test_proxies)} individual proxies...")
        if test_proxies:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_proxy = {executor.submit(test_single_proxy, proxy): proxy for proxy in test_proxies}
                
                for future in concurrent.futures.as_completed(future_to_proxy):
                    result = future.result()
                    results["individual_tests"].append(result)
        
        # Summary
        working_count = len([t for t in results["individual_tests"] if t["status"] == "OK"])
        total_tested = len(results["individual_tests"])
        
        results["summary"] = {
            "total_proxies_in_db": len(proxies),
            "proxy_source": proxy_source,
            "proxies_tested": total_tested,
            "working_proxies": working_count,
            "success_rate": f"{(working_count/total_tested*100):.1f}%" if total_tested > 0 else "0%",
            "system_status": "OK" if random_proxy and working_count > 0 else "ISSUES"
        }
        
    except Exception as e:
        results["error"] = str(e)
        results["summary"] = {"system_status": "ERROR"}
    
    return jsonify(results)


@app.route('/debug_last_timestamp')
def debug_last_timestamp():
    """Debug get_last_timestamp for all queries"""
    try:
        queries = db.get_queries()
        debug_info = []
        
        for query in queries[:5]:  # First 5 queries
            query_id = query[0]
            query_name = query[3] if len(query) > 3 and query[3] else f"Query {query_id}"
            
            # Test get_last_timestamp
            try:
                last_timestamp = db.get_last_timestamp(query_id)
                debug_info.append({
                    'query_id': query_id,
                    'query_name': query_name,
                    'last_timestamp': last_timestamp,
                    'timestamp_type': type(last_timestamp).__name__,
                    'is_none': last_timestamp is None,
                    'formatted': datetime.fromtimestamp(float(last_timestamp)).strftime('%Y-%m-%d %H:%M:%S') if last_timestamp else 'None'
                })
            except Exception as e:
                debug_info.append({
                    'query_id': query_id,
                    'query_name': query_name,
                    'error': str(e),
                    'last_timestamp': None
                })
        
        # Also check direct PostgreSQL query
        try:
            conn, db_type = db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, query_name, last_item FROM queries LIMIT 5")
            raw_data = cursor.fetchall()
            conn.close()
            
            raw_info = []
            for row in raw_data:
                raw_info.append({
                    'id': row[0],
                    'name': row[1],
                    'last_item': row[2],
                    'last_item_type': type(row[2]).__name__
                })
                
        except Exception as e:
            raw_info = [{'error': str(e)}]
        
        return jsonify({
            'status': 'success',
            'debug_info': debug_info,
            'raw_postgresql_data': raw_info,
            'db_type': db.get_db_connection()[1]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Debug error: {e}'
        })


@app.route('/redeploy_status')
def redeploy_status():
    """API endpoint для мониторинга системы автоматического редеплоя"""
    try:
        status = get_redeploy_status()
        status['monitoring_available'] = REDEPLOY_MONITORING_AVAILABLE
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting redeploy status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/proxy_status')
def proxy_status():
    """API endpoint для мониторинга системы прокси"""
    try:
        import proxies
        stats = proxies.get_proxy_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting proxy status: {e}")
        return jsonify({
            "error": str(e),
            "cache_initialized": False,
            "total_cached_proxies": 0
        }), 500

@app.route('/force_redeploy', methods=['POST'])
def force_redeploy():
    """Принудительный редеплой Railway"""
    try:
        if not REDEPLOY_MONITORING_AVAILABLE:
            return jsonify({"error": "Railway redeploy system not available"}), 503
        
        from railway_redeploy import redeploy_manager
        
        logger.info("[FORCE_REDEPLOY] Manual redeploy initiated via web interface")
        
        # Принудительно вызываем редеплой
        redeploy_manager._perform_redeploy()
        
        # Проверяем, был ли редеплой успешным
        status = redeploy_manager.get_status()
        if status.get('last_redeploy_time'):
            logger.info("[FORCE_REDEPLOY] Redeploy completed successfully")
            flash('Принудительный редеплой Railway выполнен успешно!', 'success')
            return jsonify({"success": True, "message": "Redeploy completed successfully"})
        else:
            logger.warning("[FORCE_REDEPLOY] Redeploy may have failed - no timestamp updated")
            flash('Редеплой инициирован, но статус неизвестен', 'warning')
            return jsonify({"success": True, "message": "Redeploy initiated, status unknown"})
        
    except Exception as e:
        logger.error(f"[FORCE_REDEPLOY] Error during force redeploy: {e}")
        flash(f'Ошибка при редеплое: {str(e)}', 'error')
        return jsonify({"error": str(e)}), 500

def web_ui_process():
    logger.info("Web UI process started")
    
    # Use Railway's PORT environment variable if available, otherwise fallback to configured port
    port = int(os.environ.get('PORT', configuration_values.WEB_UI_PORT))
    logger.info(f"Starting web UI on port {port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Web UI process stopped")
    except Exception as e:
        logger.error(f"Error in web UI process: {e}", exc_info=True)
