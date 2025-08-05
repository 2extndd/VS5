from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import db, core, os, re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from logger import get_logger
import configuration_values

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
                        
                        return f"SUCCESS: Found {len(items)} items, saved first item: {first_item.title}"
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

    # Get queries
    queries = db.get_queries()
    formatted_queries = []
    for i, query in enumerate(queries):
        parsed_query = urlparse(query[1])
        query_params = parse_qs(parsed_query.query)
        query_name = query[3] if query[3] is not None else query_params.get('search_text', [None])[0]

        # Get the last timestamp for this query
        try:
            last_timestamp = db.get_last_timestamp(query[0])
            last_found_item = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except:
            last_found_item = "Never"

        # Get thread_id (5th element, index 4) if available
        thread_id = None
        if len(query) > 4:
            thread_id = query[4]
            
        formatted_queries.append({
            'id': i + 1,
            'query': query[0],
            'display': query_name if query_name else query[0],
            'last_found_item': last_found_item,
            'thread_id': thread_id
        })

    # Get recent items
    items = db.get_items(limit=10)
    formatted_items = []
    for item in items:
        try:
            # Safe timestamp conversion
            try:
                timestamp_str = datetime.fromtimestamp(item[4]).strftime('%Y-%m-%d %H:%M:%S') if item[4] else 'Unknown'
            except (ValueError, TypeError, OSError):
                timestamp_str = 'Invalid timestamp'
            
            formatted_items.append({
                'id': str(item[0]) if item[0] else 'Unknown',
                'title': str(item[1]) if item[1] else 'Unknown title',
                'price': float(item[2]) if item[2] is not None else 0.0,
                'currency': str(item[3]) if item[3] else 'EUR',
                'timestamp': timestamp_str,
                'query': str(item[5]) if item[5] else 'Unknown query',
                'photo_url': str(item[6]) if item[6] else ''
            })
        except Exception as e:
            # Log the error and skip this item
            logger.error(f"Error formatting item {item}: {e}")
            continue

    # Get process status from the database
    telegram_running = db.get_parameter('telegram_process_running') == 'True'
    rss_running = db.get_parameter('rss_process_running') == 'True'

    # Get statistics for the dashboard
    stats = {
        'total_items': db.get_total_items_count(),
        'total_queries': db.get_total_queries_count(),
        'items_per_day': db.get_items_per_day()
    }

    # Get the last found item
    last_item = db.get_last_found_item()
    if last_item:
        try:
            # Safe timestamp conversion for last item
            try:
                last_timestamp_str = datetime.fromtimestamp(last_item[4]).strftime('%Y-%m-%d %H:%M:%S') if last_item[4] else 'Unknown'
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
                           queries=formatted_queries,
                           items=formatted_items,
                           telegram_running=telegram_running,
                           rss_running=rss_running,
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
            last_found_item = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except:
            last_found_item = "Never"

        # Get thread_id (5th element, index 4) if available
        thread_id = None
        if len(query) > 4:
            thread_id = query[4]
            
        formatted_queries.append({
            'id': i + 1,
            'query': query[0],
            'display': query_name if query_name else query[1],
            'last_found_item': last_found_item,
            'thread_id': thread_id
        })

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
        
        message, is_new_query = core.process_query(query, name=query_name if query_name != '' else None)
        
        if is_new_query and thread_id_int:
            # Update thread_id for the newly added query
            all_queries = db.get_queries()
            if all_queries:
                # Find the query we just added (it should be the last one or have the matching query string)
                for q in all_queries:
                    if q[1] == query:  # q[1] is the query string
                        db.update_query_thread_id(q[0], thread_id_int)  # q[0] is the query id
                        break
        
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

    items_data = db.get_items(limit=limit, query=query_string)
    formatted_items = []

    for item in items_data:
        try:
            # Safe timestamp conversion
            try:
                timestamp_str = datetime.fromtimestamp(item[4]).strftime('%Y-%m-%d %H:%M:%S') if item[4] else 'Unknown'
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
            
            formatted_items.append({
                'title': str(item[1]) if item[1] else 'Unknown title',
                'price': float(item[2]) if item[2] is not None else 0.0,
                'currency': str(item[3]) if item[3] else 'EUR',
                'timestamp': timestamp_str,
                'query': query_display,
                'url': f'https://www.vinted.de/items/{item[0]}',
                'photo_url': str(item[6]) if item[6] else ''
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
    return render_template('config.html', params=params)


@app.route('/update_config', methods=['POST'])
def update_config():
    # Update Telegram parameters
    telegram_enabled = 'telegram_enabled' in request.form
    db.set_parameter('telegram_enabled', str(telegram_enabled))
    db.set_parameter('telegram_token', request.form.get('telegram_token', ''))
    db.set_parameter('telegram_chat_id', request.form.get('telegram_chat_id', ''))

    # Update RSS parameters
    rss_enabled = 'rss_enabled' in request.form
    db.set_parameter('rss_enabled', str(rss_enabled))
    db.set_parameter('rss_port', request.form.get('rss_port', '8080'))
    db.set_parameter('rss_max_items', request.form.get('rss_max_items', '100'))

    # Update System parameters
    db.set_parameter('items_per_query', request.form.get('items_per_query', '20'))
    db.set_parameter('query_refresh_delay', request.form.get('query_refresh_delay', '60'))

    # Update Proxy parameters
    check_proxies = 'check_proxies' in request.form
    db.set_parameter('check_proxies', str(check_proxies))
    db.set_parameter('proxy_list', request.form.get('proxy_list', ''))
    db.set_parameter('proxy_list_link', request.form.get('proxy_list_link', ''))

    # Reset proxy cache to force refresh on next use
    db.set_parameter('last_proxy_check_time', "1")
    logger.info("Proxy settings updated, cache reset")

    flash('Configuration updated', 'success')
    return redirect(url_for('config'))


@app.route('/control/<process_name>/<action>', methods=['POST'])
def control_process(process_name, action):
    if process_name not in ['telegram', 'rss']:
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

        elif process_name == 'rss':
            # Check current status
            if db.get_parameter('rss_process_running') == 'True':
                return jsonify({'status': 'warning', 'message': 'RSS feed already running'})

            # Update process status in the database
            # The manager process will detect this and start the process
            db.set_parameter('rss_process_running', 'True')
            logger.info("RSS feed process start requested")
            return jsonify({'status': 'success', 'message': 'RSS feed start requested'})

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

        elif process_name == 'rss':
            # Check current status
            if db.get_parameter('rss_process_running') != 'True':
                return jsonify({'status': 'warning', 'message': 'RSS feed not running'})

            # Update process status in the database
            # The manager process will detect this and stop the process
            db.set_parameter('rss_process_running', 'False')
            logger.info("RSS feed process stop requested")
            return jsonify({'status': 'success', 'message': 'RSS feed stop requested'})

    return jsonify({'status': 'error', 'message': 'Invalid action'})


@app.route('/control/status', methods=['GET'])
def process_status():
    # Get process status from the database
    telegram_running = db.get_parameter('telegram_process_running') == 'True'
    rss_running = db.get_parameter('rss_process_running') == 'True'

    return jsonify({
        'telegram': telegram_running,
        'rss': rss_running
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

    return redirect(url_for('allowlist'))


@app.route('/remove_country/<country>', methods=['POST'])
def remove_country(country):
    message, country_list = core.process_remove_country(country)
    flash(message, 'success')

    return redirect(url_for('allowlist'))


@app.route('/clear_allowlist', methods=['POST'])
def clear_allowlist():
    db.clear_allowlist()
    flash('Allowlist cleared', 'success')

    return redirect(url_for('allowlist'))


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
