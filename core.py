import db, configuration_values, requests
from pyVintedVN import Vinted, requester
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from logger import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from datetime import datetime, timezone, timedelta

# Get logger for this module
logger = get_logger(__name__)

# Global worker statistics
_worker_stats = {}
_worker_stats_lock = threading.Lock()

# Global counter for active workers
_active_workers_count = 0
_active_workers_lock = threading.Lock()

def update_worker_stats(worker_id, status, items_count=0):
    """Update global worker statistics"""
    with _worker_stats_lock:
        if worker_id not in _worker_stats:
            _worker_stats[worker_id] = {
                'last_success': None,
                'last_error': None,
                'total_scans': 0,
                'total_items': 0,
                'total_errors': 0,
                'recent_scans': []  # Last 3 scans
            }
        
        stats = _worker_stats[worker_id]
        stats['total_scans'] += 1
        
        current_time = datetime.now(timezone(timedelta(hours=3)))
        
        if status == 'success':
            stats['last_success'] = current_time
            stats['total_items'] += items_count
            stats['recent_scans'].append({'time': current_time, 'status': 'success', 'items': items_count})
        elif status == 'error':
            stats['last_error'] = current_time
            stats['total_errors'] += 1
            stats['recent_scans'].append({'time': current_time, 'status': 'error', 'items': 0})
        
        # Keep only last 3 scans
        stats['recent_scans'] = stats['recent_scans'][-3:]

def get_worker_stats():
    """Get worker statistics for all workers"""
    with _worker_stats_lock:
        return dict(_worker_stats)

def increment_active_workers():
    """Increment active workers counter"""
    global _active_workers_count
    with _active_workers_lock:
        _active_workers_count += 1
        logger.info(f"[WORKERS] 📈 Active workers count: {_active_workers_count}")
        return _active_workers_count

def decrement_active_workers():
    """Decrement active workers counter"""
    global _active_workers_count
    with _active_workers_lock:
        _active_workers_count -= 1
        logger.warning(f"[WORKERS] 📉 Active workers count: {_active_workers_count}")
        return _active_workers_count

def get_active_workers_count():
    """Get current active workers count"""
    with _active_workers_lock:
        return _active_workers_count


def calculate_delay(published_timestamp, found_timestamp, max_hours=1):
    """Calculate delay between item publication and bot discovery
    
    Args:
        published_timestamp: When item was published (Unix timestamp)
        found_timestamp: When bot found the item (Unix timestamp)
        max_hours: Maximum hours to show (default 1). If delay > max_hours, returns None
                   This filters out incorrect timestamps (e.g. photo timestamp vs publication)
    
    Returns:
        Formatted delay string or None
    """
    try:
        if not published_timestamp or not found_timestamp:
            return None
        
        published = float(published_timestamp)
        found = float(found_timestamp)
        delay_seconds = found - published
        
        # Don't show negative delays (clock skew issues)
        if delay_seconds < 0:
            return None
        
        # Don't show delays > max_hours (likely wrong timestamp - photo vs publication)
        if delay_seconds > (max_hours * 3600):
            return None
        
        # Format delay as human-readable text
        if delay_seconds < 60:
            return f"+{int(delay_seconds)} сек"
        elif delay_seconds < 3600:
            minutes = int(delay_seconds / 60)
            return f"+{minutes} мин"
        elif delay_seconds < 86400:
            hours = int(delay_seconds / 3600)
            return f"+{hours} час" if hours == 1 else f"+{hours} часа" if hours < 5 else f"+{hours} часов"
        else:
            days = int(delay_seconds / 86400)
            return f"+{days} день" if days == 1 else f"+{days} дня" if days < 5 else f"+{days} дней"
    except (ValueError, TypeError, OSError):
        return None


def process_query(query, name=None, thread_id=None):
    """
    Process a Vinted query URL by:
    1. Parsing the URL and extracting query parameters
    2. Ensuring the order flag is set to "newest_first"
    3. Removing time and search_id parameters
    4. Rebuilding the query string and URL
    5. Checking if the query already exists in the database
    6. Adding the query to the database if it doesn't exist

    Args:
        query (str): The Vinted query URL
        name (str, optional): A name for the query. If provided, it will be used as the query name.
        thread_id (int, optional): Telegram thread ID for this query.

    Returns:
        tuple: (message, is_new_query)
            - message (str): Status message
            - is_new_query (bool): True if query was added, False if it already existed
    """
    # Parse the URL and extract the query parameters
    parsed_url = urlparse(query)
    query_params = parse_qs(parsed_url.query)

    # Ensure the order flag is set to newest_first
    query_params['order'] = ['newest_first']
    # Remove time and search_id if provided
    query_params.pop('time', None)
    query_params.pop('search_id', None)
    query_params.pop('disabled_personalization', None)
    query_params.pop('page', None)

    searched_text = query_params.get('search_text')

    # Rebuild the query string and the entire URL
    new_query = urlencode(query_params, doseq=True)
    processed_query = urlunparse(
        (parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))

    # Some queries are made with filters only, so we need to check if the search_text is present
    if db.is_query_in_db(processed_query) is True:
        return "Query already exists.", False
    else:
        # add the query to the db
        db.add_query_to_db(processed_query, name, thread_id)
        return "Query added.", True

def get_formatted_query_list():
    """
    Get a formatted list of all queries in the database.

    Returns:
        str: A formatted string with all queries, numbered
    """
    all_queries = db.get_queries()
    queries_keywords = []
    for query in all_queries:
        parsed_url = urlparse(query[1])
        query_params = parse_qs(parsed_url.query)

        # Get the name or Extract the value of 'search_text'
        query_name = query[3] if query[3] is not None else query_params.get('search_text', [None])[0]

        if query_name is None:
            # Use query text instead of the whole query object
            queries_keywords.append([query[1]])
        else:
            queries_keywords.append([query_name])

    query_list = ("\n").join([str(i + 1) + ". " + j[0] for i, j in enumerate(queries_keywords)])
    return query_list


def process_remove_query(query_id):
    """
    Process the removal of a query from the database.

    Args:
        query_id (str): The ID of the query to remove or "all" to remove all queries

    Returns:
        tuple: (message, success)
            - message (str): Status message
            - success (bool): True if query was removed successfully
    """
    if query_id == "all":
        db.remove_all_queries_from_db()
        return "All queries removed.", True

    # Validate query_id
    try:
        int(query_id)
    except (ValueError, TypeError):
        return "Invalid query ID.", False

    # Remove the query from the database
    db.remove_query_from_db(query_id)
    return "Query removed.", True


def process_add_country(country):
    """
    Process the addition of a country to the allowlist.

    Args:
        country (str): The country code to add

    Returns:
        tuple: (message, country_list)
            - message (str): Status message
            - country_list (list): Current list of allowed countries
    """
    # Format the country code (remove spaces)
    country = country.replace(" ", "")
    country_list = db.get_allowlist()

    # Validate the country code (check if it's 2 characters long)
    if len(country) != 2:
        return "Invalid country code", country_list

    # Check if the country is already in the allowlist
    # If country_list is 0, it means the allowlist is empty
    if country_list != 0 and country.upper() in country_list:
        return f'Country "{country.upper()}" already in allowlist.', country_list

    # Add the country to the allowlist
    db.add_to_allowlist(country.upper())
    return "Country added.", db.get_allowlist()


def process_remove_country(country):
    """
    Process the removal of a country from the allowlist.

    Args:
        country (str): The country code to remove

    Returns:
        tuple: (message, country_list)
            - message (str): Status message
            - country_list (list): Current list of allowed countries
    """
    # Format the country code (remove spaces)
    country = country.replace(" ", "")

    # Validate the country code (check if it's 2 characters long)
    if len(country) != 2:
        return "Invalid country code", db.get_allowlist()

    # Remove the country from the allowlist
    db.remove_from_allowlist(country.upper())
    return "Country removed.", db.get_allowlist()


def get_user_country(profile_id):
    """
    Get the country code for a Vinted user.

    Makes an API request to retrieve the user's country code.
    Handles rate limiting by trying an alternative endpoint.

    Args:
        profile_id (str): The Vinted user's profile ID

    Returns:
        str: The user's country code (2-letter ISO code) or "XX" if it can't be determined
    """
    # Users are shared between all Vinted platforms, so we can use whatever locale we want
    url = f"https://www.vinted.fr/api/v2/users/{profile_id}?localize=false"
    response = requester.get(url)
    # That's a LOT of requests, so if we get a 429 we wait a bit before retrying once
    if response.status_code == 429:
        # In case of rate limit, we're switching the endpoint. This one is slower, but it doesn't RL as soon. 
        # We're limiting the items per page to 1 to grab as little data as possible
        url = f"https://www.vinted.fr/api/v2/users/{profile_id}/items?page=1&per_page=1"
        response = requester.get(url)
        try:
            user_country = response.json()["items"][0]["user"]["country_iso_code"]
        except KeyError:
            logger.warning("Couldn't get the country due to too many requests. Returning default value.")
            user_country = "XX"
    else:
        user_country = response.json()["user"]["country_iso_code"]
    return user_country


def continuous_query_worker(query, queue, worker_index=0, start_delay=0, priority_worker_num=None):
    """
    Continuous worker that processes a SINGLE query independently.
    Each query has its own worker running in a separate thread.
    
    This implements TRUE parallel processing:
    - Query #1: scans every X sec independently with UNIQUE token & User-Agent
    - Query #2: scans every X sec independently with UNIQUE token & User-Agent
    - Query #N: scans every X sec independently with UNIQUE token & User-Agent
    
    Priority queries get 3 workers scanning every 20 seconds.
    Normal queries get 1 worker scanning at default interval.
    
    Refresh delay is read from DB DYNAMICALLY on each cycle,
    so changes in Web UI apply immediately without restart!
    
    Args:
        query: Single query tuple from database
        queue: Queue to put the items in
        worker_index: Sequential worker index (0, 1, 2...) for token assignment and stats
        start_delay: Delay before starting (for staggered priority workers)
        priority_worker_num: Priority worker number (1, 2, or 3) if this is a priority query worker
    """
    query_id = query[0]  # Database ID (may not be sequential!) - used for DB operations
    query_url = query[1]
    
    # Worker name for logging
    worker_name = f"[WORKER #Q{query_id}" + (f"-P{priority_worker_num}]" if priority_worker_num else "]")
    
    # Add delay for staggered start (priority workers)
    if start_delay > 0:
        logger.info(f"{worker_name} Waiting {start_delay:.1f}s before start (staggered)")
        time.sleep(start_delay)
    
    logger.info(f"{worker_name} 🚀 Started - will use unique token & User-Agent")
    if priority_worker_num:
        logger.info(f"{worker_name} ⚡ Priority worker #{priority_worker_num}/3 - scanning every 20s")
    logger.info(f"{worker_name} 📊 Worker lifecycle: STARTED")
    
    # Get dedicated session from token pool for THIS worker
    from token_pool import get_token_pool
    token_pool = get_token_pool()
    
    # Retry getting token up to 5 times (tokens might not be ready yet)
    token_session = None
    for retry in range(5):
        token_session = token_pool.get_session_for_worker(worker_index)  # Use worker_index, not query_id!
        if token_session:
            break
        logger.warning(f"[WORKER #{query_id}] Failed to get session, retry {retry+1}/5 in 2s...")
        time.sleep(2)
    
    if not token_session:
        logger.error(f"[WORKER #{query_id}] ❌ CRITICAL: Failed to get session after 5 retries! Worker TERMINATED!")
        decrement_active_workers()  # Worker failed to start
        return
    
    logger.info(f"[WORKER #{query_id}] Got session #{token_session.session_id} with UA: {token_session.user_agent[:50]}...")
    
    # Worker successfully started!
    increment_active_workers()
    
    # Create Vinted instance for THIS worker (will use its own session)
    vinted = Vinted(session=token_session.session)
    logger.info(f"[WORKER #{query_id}] Created Vinted instance with dedicated session")
    
    while True:
        start_time = time.time()
        
        # 🔥 ДИНАМИЧЕСКАЯ проверка priority status из БД (может измениться в Web UI!)
        current_query_data = None
        is_priority = False
        try:
            all_queries = db.get_queries()
            for q in all_queries:
                if q[0] == query_id:
                    current_query_data = q
                    is_priority = len(q) > 5 and bool(q[5])
                    break
        except Exception as e:
            logger.warning(f"{worker_name} Failed to get priority status: {e}")
        
        # 🔥 КРИТИЧНО: refresh_delay определяется ЗДЕСЬ, ДО try-except
        # Priority queries: 20s fixed, Normal queries: from config
        if is_priority:
            refresh_delay = 20  # Fixed 20s for priority queries
        else:
            refresh_delay = int(db.get_parameter("query_refresh_delay") or 60)
        
        items_per_query = int(db.get_parameter("items_per_query") or 20)
        
        # Log mode (priority or normal)
        mode_str = f"⚡ Priority mode ({refresh_delay}s)" if is_priority else f"Normal mode ({refresh_delay}s)"
        logger.debug(f"{worker_name} {mode_str}")
        
        # 🔥 НОВОЕ: Автоматическая ротация каждые 5 сканов (профилактика)
        if token_session.needs_rotation(rotation_interval=5):
            logger.info(f"{worker_name} 🔄 Auto-rotation: {token_session.scan_count} scans completed, getting fresh Token+Proxy pair...")
            new_session = token_pool.create_fresh_pair(worker_index)
            if new_session:
                token_session = new_session
                vinted = Vinted(session=token_session.session)
                logger.info(f"[WORKER #{query_id}] ✅ Auto-rotation complete: New session #{token_session.session_id}")
            else:
                # Auto-rotation failed (probably 403 global ban)
                # Reset counter to wait another 5 cycles before retry
                token_session.scan_count = 0
                logger.error(f"[WORKER #{query_id}] ❌ Auto-rotation failed, continuing with old session (will retry in 5 scans)")
        
        # 🔥 КРИТИЧНО: Проверяем токен ПЕРЕД каждым сканированием!
        # Если токен стал невалидным - заменяем его
        elif not token_session.is_valid:
            logger.warning(f"[WORKER #{query_id}] Token invalid - getting fresh Token+Proxy pair...")
            new_session = token_pool.create_fresh_pair(worker_index)
            if new_session:
                token_session = new_session
                vinted = Vinted(session=token_session.session)
                logger.info(f"[WORKER #{query_id}] ✅ Got fresh pair: session #{token_session.session_id}")
            else:
                # Failed to create new pair - continue with invalid session (will try again next cycle)
                logger.error(f"[WORKER #{query_id}] ❌ Failed to get fresh pair, continuing with invalid session")
        
        try:
            # Scan this query using THIS worker's dedicated Vinted instance
            logger.debug(f"[WORKER #{query_id}] 🔍 Starting Vinted API request...")
            search_result = vinted.items.search(query_url, nbr_items=items_per_query)
            logger.debug(f"[WORKER #{query_id}] ✅ Vinted API request completed")

            elapsed = time.time() - start_time

            # Check if we got an error response (tuple) or successful items (list)
            if isinstance(search_result, tuple) and len(search_result) == 2:
                response, status_code = search_result

                # Report HTTP error to redeploy system
                from railway_redeploy import report_403_error, report_401_error, report_429_error

                if status_code == 403:
                    report_403_error()
                    logger.warning(f"[WORKER #{query_id}] 403 error reported to redeploy system")
                elif status_code == 401:
                    report_401_error()
                    logger.warning(f"[WORKER #{query_id}] 401 error reported to redeploy system")
                elif status_code == 429:
                    report_429_error()
                    logger.warning(f"[WORKER #{query_id}] 429 error reported to redeploy system")

                # Report error to token pool as well
                token_pool.report_error(token_session)

                # Update worker stats (error) - use worker_index for correct counting
                update_worker_stats(worker_index, 'error')

                # 🔥 КРИТИЧНО: При 403/401 - НЕМЕДЛЕННО получить НОВУЮ ПАРУ и повторить!
                if status_code in (403, 401):
                    logger.warning(f"[WORKER #{query_id}] 🔄 Got {status_code} - attempting IMMEDIATE retry with NEW Token+Proxy pair...")
                    
                    # Попытка получить новую ПАРУ (Token + Proxy) и повторить запрос (до 3 попыток)
                    retry_success = False
                    for retry_attempt in range(3):
                        # Получаем НОВУЮ ПАРУ (Token + Proxy)
                        logger.info(f"[WORKER #{query_id}] 🔑 Getting fresh Token+Proxy pair (retry {retry_attempt + 1}/3)...")
                        new_session = token_pool.create_fresh_pair(worker_index)  # Fresh pair!
                        
                        if not new_session:
                            logger.warning(f"[WORKER #{query_id}] Failed to get fresh pair for retry {retry_attempt + 1}/3")
                            time.sleep(1)  # Короткая пауза перед следующей попыткой
                            continue
                        
                        # Обновляем токен и сессию
                        token_session = new_session
                        vinted = Vinted(session=token_session.session)
                        logger.info(f"[WORKER #{query_id}] ✅ Got new token #{token_session.session_id}, retrying request...")
                        
                        # Повторяем запрос с новым токеном
                        retry_start = time.time()
                        retry_result = vinted.items.search(query_url, nbr_items=items_per_query)
                        retry_elapsed = time.time() - retry_start
                        
                        # Проверяем результат retry
                        if isinstance(retry_result, tuple) and len(retry_result) == 2:
                            retry_response, retry_status = retry_result
                            logger.warning(f"[WORKER #{query_id}] Retry {retry_attempt + 1}/3 failed with HTTP {retry_status} ({retry_elapsed:.2f}s)")
                            token_pool.report_error(token_session)
                            
                            # Если снова 403/401 - пробуем следующий токен
                            if retry_status in (403, 401):
                                continue
                            else:
                                # Другая ошибка - выходим из retry-цикла
                                break
                        else:
                            # Успех! Обрабатываем результат
                            search_result = retry_result
                            elapsed = retry_elapsed
                            retry_success = True
                            logger.info(f"[WORKER #{query_id}] 🎉 Retry successful with new token after {retry_elapsed:.2f}s!")
                            token_pool.report_success(token_session)
                            break
                    
                    # Если retry успешен - обрабатываем результат как обычно (переходим к блоку else ниже)
                    if not retry_success:
                        logger.error(f"[WORKER #{query_id}] ❌ All 3 retry attempts failed - will wait {refresh_delay}s before next scan")
                    else:
                        # Перенаправляем в success блок
                        all_items = search_result
                        token_pool.report_success(token_session)
                        from railway_redeploy import report_success
                        report_success()
                        
                        if all_items:
                            queue.put((all_items, query_id))
                            logger.info(f"[WORKER #{query_id}] ✅ Found {len(all_items)} items after retry in {elapsed:.2f}s (next scan in {refresh_delay}s)")
                            update_worker_stats(worker_index, 'success', len(all_items))
                        else:
                            logger.info(f"[WORKER #{query_id}] 📭 No new items after retry ({elapsed:.2f}s, next scan in {refresh_delay}s)")
                            update_worker_stats(worker_index, 'success', 0)
                        
                        # 🔥 Инкрементируем счетчик сканов после успешного retry
                        token_session.increment_scan()
                        logger.debug(f"[WORKER #{query_id}] Scan counter after retry: {token_session.scan_count}/5")
                else:
                    # Для 429 и других ошибок - просто ждем refresh_delay
                    logger.error(f"[WORKER #{query_id}] ❌ HTTP {status_code} error after {elapsed:.2f}s - will retry in {refresh_delay}s")
            else:
                # Successful scan - got items list
                all_items = search_result

                # Report successful request to token pool AND redeploy system
                token_pool.report_success(token_session)

                # Report success to redeploy system for success streak
                from railway_redeploy import report_success
                report_success()

                # Put items into queue
                if all_items:
                    queue.put((all_items, query_id))
                    logger.info(f"[WORKER #{query_id}] ✅ Found {len(all_items)} items in {elapsed:.2f}s (next scan in {refresh_delay}s)")
                    # Update worker stats - use worker_index for correct counting
                    update_worker_stats(worker_index, 'success', len(all_items))
                else:
                    logger.info(f"[WORKER #{query_id}] 📭 No new items ({elapsed:.2f}s, next scan in {refresh_delay}s)")
                    # Update worker stats (successful scan, but no items) - use worker_index
                    update_worker_stats(worker_index, 'success', 0)
                
                # 🔥 НОВОЕ: Инкрементируем счетчик сканов (для автоматической ротации)
                token_session.increment_scan()
                logger.debug(f"[WORKER #{query_id}] Scan counter: {token_session.scan_count}/5")

        except Exception as e:
            elapsed = time.time() - start_time
            
            # Report error to token pool
            token_pool.report_error(token_session)

            # Update worker stats (error) - use worker_index for correct counting
            update_worker_stats(worker_index, 'error')

            # Report generic error to redeploy system (fallback)
            from railway_redeploy import report_403_error
            report_403_error()
            
            logger.error(f"[WORKER #{query_id}] ❌ Unexpected error after {elapsed:.2f}s: {e} - will retry in {refresh_delay}s")

            # Token pool automatically replaces invalid tokens on next get_session_for_worker() call
            # No need to manually check is_valid here - will be checked on next iteration
        
        # 🔥 КРИТИЧНО: Sleep ВСЕГДА с одинаковой задержкой
        # refresh_delay определен ДО try-except, поэтому ВСЕГДА доступен
        time.sleep(refresh_delay)


def start_continuous_workers(queue):
    """
    Start independent continuous workers for EACH query.
    
    Architecture:
    - N queries = N independent threads (e.g. 72 queries = 72 workers)
    - Each worker has UNIQUE token & User-Agent from token pool
    - Each thread scans its own query dynamically (reads delay from DB)
    - All threads run in parallel forever
    - Query Refresh Delay applies to EACH query independently
    - Changes in Web UI apply IMMEDIATELY (no restart needed!)
    - System automatically scales: add 100 queries → 100 workers + 100 tokens!
    
    This is the TRUE parallel query processing with maximum diversification!
    """
    try:
        logger.info(f"[WORKERS] 🚀 Starting INDEPENDENT workers for each query...")
        
        all_queries = db.get_queries()
        num_queries = len(all_queries)
        
        # Count priority and normal queries
        priority_count = sum(1 for q in all_queries if len(q) > 5 and bool(q[5]))
        normal_count = num_queries - priority_count
        total_workers = normal_count + (priority_count * 3)  # 3 workers per priority query
        
        logger.info(f"[WORKERS] Got {num_queries} queries ({normal_count} normal, {priority_count} priority)")
        logger.info(f"[WORKERS] 📊 ARCHITECTURE: {total_workers} workers ({normal_count}×1 + {priority_count}×3)")
        logger.info(f"[WORKERS] ⚡ Priority queries: 3 workers each, scanning every 20s")
        logger.info(f"[WORKERS] 📊 Normal queries: 1 worker each, scanning at default interval")
        
        # Initialize token pool with size matching TOTAL number of workers
        # 🔥 НОВОЕ: Токены создаются ПАРАЛЛЕЛЬНО (10 потоков) - быстрый старт!
        from token_pool import get_token_pool
        token_pool = get_token_pool(target_size=total_workers, prewarm=True)  # ПАРАЛЛЕЛЬНОЕ создание!
        logger.info(f"[WORKERS] 🎯 Token pool ready with {total_workers} tokens!")
        logger.info(f"[WORKERS] ⚡ Tokens created IN PARALLEL (10 threads) - FAST startup!")
        logger.info(f"[WORKERS] 🚀 All workers can start IMMEDIATELY with ready tokens!")
        
        # Get INITIAL configuration (for logging only)
        refresh_delay = int(db.get_parameter("query_refresh_delay") or 60)
        items_per_query = int(db.get_parameter("items_per_query") or 20)
        
        logger.info(f"[WORKERS] Initial config: {refresh_delay}s delay, {items_per_query} items per query")
        logger.info(f"[WORKERS] Workers will read FRESH config from DB on each cycle (dynamic!)")
        logger.info(f"[WORKERS] Changes in Web UI will apply IMMEDIATELY without restart! 🔥")
        
        # Start ALL workers
        executor = ThreadPoolExecutor(max_workers=total_workers)
        
        logger.info(f"[WORKERS] 🚀 Starting {total_workers} workers...")
        
        # Reset active workers counter
        global _active_workers_count
        with _active_workers_lock:
            _active_workers_count = 0
        
        worker_index = 0  # Global worker index for token assignment
        
        for query in all_queries:
            query_id = query[0]
            is_priority = len(query) > 5 and bool(query[5])
            
            if is_priority:
                # Create 3 workers for priority query with staggered start
                logger.info(f"[WORKERS] ⚡ Creating 3 priority workers for Query #{query_id}")
                for priority_idx in range(3):
                    start_delay = priority_idx * 7  # 0s, 7s, 14s stagger
                    executor.submit(
                        continuous_query_worker, 
                        query, 
                        queue, 
                        worker_index=worker_index,
                        start_delay=start_delay,
                        priority_worker_num=priority_idx + 1  # 1, 2, 3
                    )
                    worker_index += 1
            else:
                # Create 1 worker for normal query
                executor.submit(
                    continuous_query_worker, 
                    query, 
                    queue, 
                    worker_index=worker_index,
                    start_delay=0
                )
                worker_index += 1
        
        logger.info(f"[WORKERS] ✅ {total_workers} independent workers SUBMITTED to executor!")
        logger.info(f"[WORKERS] ⏳ Waiting 15 seconds for workers to initialize and report...")
        
        # Wait for workers to initialize and report their status
        time.sleep(15)
        
        active_count = get_active_workers_count()
        logger.info(f"[WORKERS] 📊 FINAL COUNT: {active_count}/{total_workers} workers are ACTIVE!")
        
        if active_count < total_workers:
            logger.error(f"[WORKERS] ⚠️ WARNING: {total_workers - active_count} workers FAILED TO START!")
            logger.error(f"[WORKERS] ⚠️ Expected {total_workers} workers, but only {active_count} are running!")
        else:
            logger.info(f"[WORKERS] ✅ All {active_count} workers are running successfully!")
        
        logger.info(f"[WORKERS] 🔥 All queries scanning in TRUE PARALLEL with DYNAMIC config!")
        logger.info(f"[WORKERS] ⚡ Priority queries scan every 20s (3 workers each)")
        logger.info(f"[WORKERS] ⚡ Normal queries scan every {refresh_delay}s (1 worker each)")
        
        # Keep executor alive
        return executor
        
    except Exception as e:
        logger.error(f"[WORKERS] CRITICAL ERROR starting workers: {e}")
        import traceback
        logger.error(f"[WORKERS] Traceback: {traceback.format_exc()}")
        return None


def process_items(queue):
    """
    DEPRECATED: This function is no longer used with continuous workers.
    Keeping for backward compatibility.
    """
    logger.warning("[DEPRECATED] process_items() called - this should not happen with continuous workers!")
    pass


def clear_item_queue(items_queue, new_items_queue):
    """
    Process items from the items_queue.
    This function is scheduled to run frequently.
    
    🔥 КРИТИЧНО: Обрабатывает ВСЕ элементы в очереди за один вызов!
    Иначе при 72 воркерах очередь растет быстрее, чем обрабатывается!
    """
    processed_count = 0
    
    # 🔥 КРИТИЧНО: Кешируем queries ОДИН РАЗ перед обработкой!
    # Иначе db.get_queries() вызывается для КАЖДОЙ вещи (1440+ раз за цикл!)
    all_queries_cache = db.get_queries()
    logger.debug(f"[QUEUE] Cached {len(all_queries_cache)} queries for fast lookup")
    
    # Обрабатываем ВСЕ элементы в очереди (до 100 за раз для безопасности)
    while not items_queue.empty() and processed_count < 100:
        try:
            data, query_id = items_queue.get_nowait()
            processed_count += 1
            
            logger.debug(f"[QUEUE] Processing batch #{processed_count}: {len(data)} items from query #{query_id}")
            
            for item in reversed(data):
                logger.debug(f"[QUEUE] Processing item {item.id}: {item.title[:50]}...")

                # Check if item already exists in database
                if db.is_item_in_db_by_id(item.id):
                    logger.debug(f"[QUEUE] Item {item.id} already exists in database, skipping...")
                    continue
                    
                # TEMPORARILY DISABLE TIME FILTER - accept all items but check for duplicates
                if True:  # Accept all items for now
                    logger.debug(f"[QUEUE] Creating message for item {item.id}...")
                    try:
                        # Calculate delay between publication and discovery
                        import time
                        found_at = time.time()  # Record when bot found this item
                        delay_str = calculate_delay(item.raw_timestamp, found_at)
                        
                        # Format price with delay
                        price_text = f"💶{str(item.price)} {item.currency}"
                        if delay_str:
                            price_text += f" ({delay_str})"
                        
                        # We create the message with conditional size display
                        if item.size_title and item.size_title.strip():
                            # Format message with size
                            content = f"<b>{item.title}</b>\n<b>{price_text}</b>\n⛓️ {item.size_title}\n{item.brand_title}"
                        else:
                            # Format message without size line
                            content = f"<b>{item.title}</b>\n<b>{price_text}</b>\n{item.brand_title}"
                        
                        # Add invisible image link if photo exists
                        if item.photo:
                            content += f"\n<a href='{item.photo}'>&#8205;</a>"
                        
                        # IMPORTANT: Save to DB FIRST, then send to Telegram
                        # This prevents items appearing in TG but not in Web UI if DB fails
                        
                        # Add the item to the db (found_at already calculated above for delay)
                        db_save_success = db.add_item_to_db(id=item.id, title=item.title, query_id=query_id, price=item.price, 
                                          timestamp=item.raw_timestamp, photo_url=item.photo, currency=item.currency, 
                                          brand_title=item.brand_title, found_at=found_at)
                        
                        if not db_save_success:
                            logger.error(f"[QUEUE] ❌ FAILED to save item {item.id} to database! Skipping Telegram send.")
                            continue  # Don't send to Telegram if DB save failed!
                        
                        logger.debug(f"[QUEUE] ✅ Item {item.id} saved to database successfully")
                        
                        # Update the query's last_found timestamp
                        db.update_query_last_found(query_id, item.raw_timestamp)
                        
                        # Get thread_id for this query from CACHED queries
                        thread_id = None
                        try:
                            # Use cached queries instead of calling db.get_queries() for EVERY item!
                            current_query = next((q for q in all_queries_cache if q[0] == query_id), None)
                            if current_query and len(current_query) > 4:
                                thread_id = current_query[4]  # thread_id is the 5th element (index 4)
                        except Exception as e:
                            logger.warning(f"Could not get thread_id for query {query_id}: {e}")
                        
                        # NOW add to Telegram queue (only after successful DB save)
                        new_items_queue.put((content, item.url, "Open Vinted", None, None, thread_id, item.photo))
                        
                        logger.info(f"[QUEUE] ✅ NEW ITEM: {item.title} ({delay_str})")
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to process item {item.id}: {e}")
                        import traceback
                        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        except Exception as e:
            logger.error(f"[QUEUE] Error processing queue batch: {e}")
            break
    
    if processed_count > 0:
        logger.info(f"[QUEUE] ✅ Processed {processed_count} batches from queue")


def check_version():
    """
    Check if the application is up to date
    """
    try:
        # Get URL from the database
        github_url = db.get_parameter("github_url")
        # Get version from the database
        ver = db.get_parameter("version")
        # Get latest version from the repository
        url = f"{github_url}/releases/latest"
        response = requests.get(url)

        if response.status_code == 200:
            latest_version = response.url.split('/')[-1]
            is_up_to_date = (ver == latest_version)
            return is_up_to_date, ver, latest_version, github_url
        else:
            # If we can't check, assume it's up to date
            return True, ver, ver, github_url
    except Exception as e:
        logger.error(f"Error checking for new version: {str(e)}", exc_info=True)
        # If we can't check, assume it's up to date
        return True, ver, ver, github_url
