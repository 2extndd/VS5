import random
import requests
import time
from requests.exceptions import RequestException
import configuration_values
import concurrent.futures
from typing import List, Optional
from logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Cache for proxy list
_PROXY_CACHE = None
_PROXY_CACHE_INITIALIZED = False
_SINGLE_PROXY = None

# URL to test proxies against
_TEST_URL = "https://www.vinted.de/"
_TEST_TIMEOUT = 10  # seconds (increased from 2 to avoid false negatives)
# Maximum number of concurrent workers for proxy checking
MAX_PROXY_WORKERS = 10
# Time interval in seconds after which proxies should be rechecked (30 minutes)
PROXY_RECHECK_INTERVAL = 30 * 60

def fetch_proxies_from_link(url: str) -> List[str]:
    """
    Fetch proxies from a URL.

    Args:
        url (str): URL to fetch proxies from.

    Returns:
        List[str]: List of proxies.
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Split by newlines and filter out empty lines
            return [line.strip() for line in response.text.splitlines() if line.strip()]
        return []
    except Exception:
        # If there's any error fetching proxies, return an empty list
        return []

def check_proxies_parallel(proxies_list: List[str]) -> List[str]:
    """
    Check multiple proxies in parallel using a thread pool.

    Args:
        proxies_list (List[str]): List of proxy strings to check.

    Returns:
        List[str]: List of working proxies.
    """
    working_proxies = []

    # Use ThreadPoolExecutor to check proxies in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PROXY_WORKERS) as executor:
        # Submit all proxy checking tasks
        future_to_proxy = {executor.submit(check_proxy, proxy): proxy for proxy in proxies_list}

        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_proxy):
            proxy = future_to_proxy[future]
            try:
                is_working = future.result()
                if is_working:
                    working_proxies.append(proxy)
            except Exception:
                # If an exception occurred during checking, consider the proxy not working
                pass

    return working_proxies


def get_random_proxy() -> Optional[str]:
    """
    Get a random proxy from the configuration values.

    Uses a cache to minimize I/O operations:
    - If there are no proxies on first check, never checks again
    - If there is only one proxy, always returns that one
    - Otherwise, returns a random proxy from the cached list

    Proxies are checked in parallel to avoid blocking the main thread.
    Proxies are rechecked if they were checked more than PROXY_RECHECK_INTERVAL seconds ago.

    Returns:
        Optional[str]: A randomly selected proxy string or None if no working proxies are found.
    """
    global _PROXY_CACHE, _PROXY_CACHE_INITIALIZED, _SINGLE_PROXY
    
    logger.debug(f"[PROXY] get_random_proxy() called")
    logger.debug(f"[PROXY] Cache initialized: {_PROXY_CACHE_INITIALIZED}")
    logger.debug(f"[PROXY] Cache size: {len(_PROXY_CACHE) if _PROXY_CACHE else 0}")
    logger.debug(f"[PROXY] Single proxy mode: {_SINGLE_PROXY is not None}")

    # Import db here to avoid circular imports
    import db

    current_time = time.time()

    # Get the last proxy check time from the database
    last_proxy_check_time_str = db.get_parameter("last_proxy_check_time")
    last_proxy_check_time = float(last_proxy_check_time_str) if last_proxy_check_time_str else 0

    # Check if we need to recheck proxies (if more than PROXY_RECHECK_INTERVAL seconds have passed)
    if (_PROXY_CACHE_INITIALIZED and
            last_proxy_check_time > 0 and
            current_time - last_proxy_check_time > PROXY_RECHECK_INTERVAL):
        # Reset cache to force recheck
        _PROXY_CACHE_INITIALIZED = False
        _PROXY_CACHE = None
        _SINGLE_PROXY = None

    # If cache is already initialized
    if _PROXY_CACHE_INITIALIZED:
        # If we determined there are no proxies, always return None
        if _PROXY_CACHE is None:
            return None
        # If we have a single proxy, always return that one
        if _SINGLE_PROXY is not None:
            return _SINGLE_PROXY
        # Otherwise, return a random proxy from the cache
        if _PROXY_CACHE:
            return random.choice(_PROXY_CACHE)
        return None

    # Initialize cache on first call or after recheck interval
    _PROXY_CACHE_INITIALIZED = True

    # Update the last check time in the database
    db.set_parameter("last_proxy_check_time", str(current_time))

    # Initialize all_proxies list
    all_proxies = []

    # Check if PROXY_LIST_LINK is configured first (priority over manual list)
    proxy_list_link = db.get_parameter("proxy_list_link")
    if proxy_list_link:
        logger.info(f"[PROXY] Fetching proxies from link: {proxy_list_link}")
        # Fetch proxies from the link
        link_proxies = fetch_proxies_from_link(proxy_list_link)
        logger.info(f"[PROXY] Fetched {len(link_proxies)} proxies from link")
        
        # Convert WebShare format to standard format
        converted_proxies = []
        for proxy in link_proxies:
            parts = proxy.strip().split(':')
            if len(parts) == 4 and not ('://' in proxy or '@' in proxy):
                # WebShare format: ip:port:user:pass -> http://user:pass@ip:port
                converted_proxies.append(convert_webshare_to_standard(proxy))
            else:
                converted_proxies.append(proxy)
        all_proxies = converted_proxies
        logger.info(f"[PROXY] Using proxies from link (ignoring manual proxy_list to avoid duplicates)")
    else:
        # If no link, use manual PROXY_LIST from database
        proxy_list = db.get_parameter("proxy_list")
        logger.info(f"[PROXY] proxy_list from DB: {proxy_list[:100] if proxy_list else 'None'}{'...' if proxy_list and len(proxy_list) > 100 else ''}")
        if proxy_list:
            try:
                # If PROXY_LIST is stored as a Python list string representation, eval it
                if proxy_list.startswith('[') and proxy_list.endswith(']'):
                    all_proxies = eval(proxy_list)
                else:
                    # If PROXY_LIST is a string with multiple proxies separated by semicolons OR newlines
                    # First try splitting by newlines (for column format)
                    proxies_by_lines = [p.strip() for p in proxy_list.split('\n') if p.strip()]
                    if len(proxies_by_lines) > 1:
                        # Multiple lines found - use line-by-line format
                        all_proxies = proxies_by_lines
                    else:
                        # Single line or no newlines - use semicolon format
                        all_proxies = [p.strip() for p in proxy_list.split(';') if p.strip()]
                    
                    # Convert WebShare format proxies to standard format
                    converted_proxies = []
                    for proxy in all_proxies:
                        parts = proxy.strip().split(':')
                        if len(parts) == 4 and not ('://' in proxy or '@' in proxy):
                            # WebShare format: ip:port:user:pass -> http://user:pass@ip:port
                            converted_proxies.append(convert_webshare_to_standard(proxy))
                        else:
                            converted_proxies.append(proxy)
                    all_proxies = converted_proxies
                logger.info(f"[PROXY] Parsed {len(all_proxies)} proxies from proxy_list")
            except Exception as e:
                logger.error(f"[PROXY] Error parsing proxy_list: {e}")
                all_proxies = []
    
    # Deduplicate proxies (just in case)
    all_proxies = list(dict.fromkeys(all_proxies))
    logger.info(f"[PROXY] Total unique proxies collected: {len(all_proxies)}")

    # Check proxies in parallel if we have any and CHECK_PROXIES is True
    if all_proxies:
        check_proxies = db.get_parameter("check_proxies") == "True"
        logger.info(f"[PROXY] check_proxies setting: {check_proxies}")
        if check_proxies:
            logger.info(f"[PROXY] Starting parallel proxy validation...")
            working_proxies = check_proxies_parallel(all_proxies)
            logger.info(f"[PROXY] Proxy validation complete: {len(working_proxies)} working out of {len(all_proxies)}")
            if working_proxies:
                _PROXY_CACHE = working_proxies
                # If there's only one working proxy, cache it separately
                if len(working_proxies) == 1:
                    _SINGLE_PROXY = working_proxies[0]
                    logger.info(f"[PROXY] Using single validated proxy: {_SINGLE_PROXY}")
                    return _SINGLE_PROXY
                selected_proxy = random.choice(working_proxies)
                logger.info(f"[PROXY] Selected random validated proxy: {selected_proxy}")
                return selected_proxy
            else:
                logger.warning(f"[PROXY] No working proxies found after validation!")
        else:
            # If CHECK_PROXIES is False, just cache all proxies without checking them
            logger.info(f"[PROXY] Using all {len(all_proxies)} proxies without validation")
            _PROXY_CACHE = all_proxies
            # If there's only one proxy, cache it separately
            if len(all_proxies) == 1:
                _SINGLE_PROXY = all_proxies[0]
                logger.info(f"[PROXY] Using single unvalidated proxy: {_SINGLE_PROXY}")
                return _SINGLE_PROXY
            selected_proxy = random.choice(all_proxies)
            logger.info(f"[PROXY] Selected random unvalidated proxy: {selected_proxy}")
            return selected_proxy

    # No working proxies found
    logger.warning(f"[PROXY] No proxies available - using direct connection")
    _PROXY_CACHE = None
    return None


def check_proxy(proxy: str) -> bool:
    """
    Check if a proxy is working by making a request to the test URL.

    This function is thread-safe as it creates a new session for each check.
    Uses a random user agent to avoid detection.

    Args:
        proxy (str): Proxy string to check.

    Returns:
        bool: True if the proxy is working, False otherwise.
    """
    if proxy is None:
        return False

    # Convert proxy string to dictionary format
    proxy_dict = convert_proxy_string_to_dict(proxy)
    proxy_display = f"{proxy[:20]}..." if len(proxy) > 20 else proxy

    try:
        # Create a new session for testing (ensures thread safety)
        session = requests.Session()

        # Set random user agent and default headers
        headers = {
            "User-Agent": random.choice(configuration_values.USER_AGENTS),
            **configuration_values.DEFAULT_HEADERS
        }
        session.headers.update(headers)

        # Make a HEAD request to the test URL with the proxy
        start_time = time.time()
        response = session.head(_TEST_URL, proxies=proxy_dict, timeout=_TEST_TIMEOUT, allow_redirects=True)
        response_time = round((time.time() - start_time) * 1000, 2)

        # Check if the request was successful (accept 2xx and 3xx codes)
        is_working = 200 <= response.status_code < 400
        if is_working:
            logger.info(f"[PROXY] ✅ {proxy_display} - OK (HTTP {response.status_code}, {response_time}ms)")
        else:
            logger.warning(f"[PROXY] ❌ {proxy_display} - HTTP {response.status_code}")
        return is_working
    except (RequestException, ConnectionError, TimeoutError) as e:
        logger.warning(f"[PROXY] ❌ {proxy_display} - {type(e).__name__}: {str(e)[:50]}")
        return False
    except Exception as e:
        # Catch any other exceptions to prevent process crashes
        logger.warning(f"[PROXY] ❌ {proxy_display} - Unexpected error: {str(e)[:50]}")
        return False
    finally:
        # Ensure the session is closed to prevent resource leaks
        if 'session' in locals():
            session.close()


def convert_webshare_to_standard(proxy: str) -> str:
    """
    Convert WebShare format (ip:port:user:pass) to standard format (http://user:pass@ip:port)
    
    Args:
        proxy (str): Proxy in WebShare format
        
    Returns:
        str: Proxy in standard format
    """
    parts = proxy.strip().split(':')
    if len(parts) == 4:
        ip, port, user, password = parts
        return f"http://{user}:{password}@{ip}:{port}"
    return proxy

def convert_proxy_string_to_dict(proxy: Optional[str]) -> dict:
    """
    Convert a proxy string to a dictionary format.
    Supports formats:
    - ip:port
    - user:pass@ip:port  
    - protocol://ip:port
    - protocol://user:pass@ip:port
    - ip:port:user:pass (WebShare format)

    Args:
        proxy (Optional[str]): Proxy string to convert.

    Returns:
        dict: Proxy configuration dictionary.
    """
    if proxy is None:
        return {}

    # Check if it's WebShare format (ip:port:user:pass)
    parts = proxy.strip().split(':')
    if len(parts) == 4 and not ('://' in proxy or '@' in proxy):
        # Convert WebShare format to standard format
        proxy = convert_webshare_to_standard(proxy)

    # Handle protocol-specified proxies
    if '://' in proxy:
        protocol, address = proxy.split('://', 1)
        
        # Check if there's authentication info
        if '@' in address:
            # Format: protocol://user:pass@ip:port
            auth_part, host_part = address.split('@', 1)
            proxy_url = f"{protocol}://{auth_part}@{host_part}"
        else:
            # Format: protocol://ip:port
            proxy_url = proxy
            
        if protocol == "http":
            return {"http": proxy_url, "https": proxy_url}
        return {protocol: proxy_url}
    else:
        # No protocol specified
        if '@' in proxy:
            # Format: user:pass@ip:port
            auth_part, host_part = proxy.split('@', 1)
            proxy_url = f"http://{auth_part}@{host_part}"
        else:
            # Format: ip:port
            proxy_url = f"http://{proxy}"
            
        return {"http": proxy_url, "https": proxy_url}


def get_fresh_proxy(exclude_proxy: Optional[str] = None) -> Optional[str]:
    """
    Получить новый прокси, исключая указанный (для ротации).
    
    Args:
        exclude_proxy (Optional[str]): Прокси, который нужно исключить из выбора
        
    Returns:
        Optional[str]: Новый прокси или None если нет альтернатив
    """
    global _PROXY_CACHE, _PROXY_CACHE_INITIALIZED
    
    logger.info(f"[PROXY] get_fresh_proxy() called, excluding: {exclude_proxy}")
    
    # Import db here to avoid circular imports
    import db
    
    # Если кэш не инициализирован, инициализируем его
    if not _PROXY_CACHE_INITIALIZED:
        get_random_proxy()  # Это инициализирует кэш
    
    # Если нет прокси в кэше
    if _PROXY_CACHE is None or not _PROXY_CACHE:
        logger.info(f"[PROXY] No proxies available in cache")
        return None
    
    # Если только один прокси и он исключается
    if len(_PROXY_CACHE) == 1 and _PROXY_CACHE[0] == exclude_proxy:
        logger.info(f"[PROXY] Only one proxy available and it's excluded")
        return None
    
    # Фильтруем исключенный прокси
    available_proxies = [p for p in _PROXY_CACHE if p != exclude_proxy]
    
    if not available_proxies:
        logger.info(f"[PROXY] No alternative proxies available after filtering")
        return None
    
    # Возвращаем случайный из доступных
    selected_proxy = random.choice(available_proxies)
    logger.info(f"[PROXY] Selected fresh proxy: {selected_proxy}")
    return selected_proxy


def get_proxy_statistics() -> dict:
    """
    Получить статистику использования прокси
    
    Returns:
        dict: Статистика прокси
    """
    global _PROXY_CACHE, _PROXY_CACHE_INITIALIZED, _SINGLE_PROXY
    
    # Import db here to avoid circular imports
    import db
    
    # Для множественных прокси показываем пример случайного
    current_proxy_display = _SINGLE_PROXY
    if not current_proxy_display and _PROXY_CACHE:
        current_proxy_display = f"Random from {len(_PROXY_CACHE)} proxies (e.g., {_PROXY_CACHE[0][:20]}...)"
    
    stats = {
        "cache_initialized": _PROXY_CACHE_INITIALIZED,
        "total_cached_proxies": len(_PROXY_CACHE) if _PROXY_CACHE else 0,
        "single_proxy_mode": _SINGLE_PROXY is not None,
        "current_single_proxy": current_proxy_display,
        "proxy_check_enabled": db.get_parameter("check_proxies") == "True",
        "last_check_time": db.get_parameter("last_proxy_check_time"),
        "proxy_list_configured": bool(db.get_parameter("proxy_list")),
        "proxy_link_configured": bool(db.get_parameter("proxy_list_link")),
        "proxy_recheck_interval_hours": PROXY_RECHECK_INTERVAL / 3600
    }
    
    # Маскируем чувствительные данные
    if stats["current_single_proxy"] and '@' in str(stats["current_single_proxy"]):
        import re
        stats["current_single_proxy"] = re.sub(r'://[^:]+:[^@]+@', '://***:***@', str(stats["current_single_proxy"]))
    
    return stats


def configure_proxy(session: requests.Session, proxy: Optional[str] = None) -> bool:
    """
    Configure the proxy settings for a requests session.

    Args:
        session (requests.Session): The session to configure.
        proxy (Optional[str], optional): Proxy to be used. If None, a random proxy will be selected.

    Returns:
        bool: True if proxy was configured, False otherwise.
    """
    # If no proxy is provided, get a random one
    if proxy is None:
        proxy = get_random_proxy()

    # If we still don't have a proxy, return False (KEEP existing proxy, don't clear!)
    if proxy is None:
        logger.warning("[PROXY] No proxy available - keeping current proxy configuration")
        return False

    # Handle string proxy
    if isinstance(proxy, str):
        proxy = convert_proxy_string_to_dict(proxy)

    # Update the session with the proxy settings
    session.proxies.update(proxy)
    logger.info(f"[PROXY] Proxy configured for session: {proxy}")
    return True
