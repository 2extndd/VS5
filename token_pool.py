"""
Token Pool Manager for distributed Vinted scraping.

This module manages a pool of independent sessions with unique tokens and User-Agents.
Each worker gets its own session to avoid detection by Vinted's anti-bot systems.
"""
import requests
import random
import threading
import time
from logger import get_logger

logger = get_logger(__name__)

# Pool of realistic User-Agents (Chrome, Firefox, Edge - latest versions)
USER_AGENTS = [
    # Chrome variants
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    
    # Firefox variants
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Edge variants
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]


class TokenSession:
    """
    Represents a single session with unique token, User-Agent, AND proxy.
    Token and proxy are BOUND together - they live and die together!
    """
    def __init__(self, session_id, session, access_token, user_agent, proxy):
        self.session_id = session_id
        self.session = session
        self.access_token = access_token
        self.user_agent = user_agent
        self.proxy = proxy  # Proxy bound to this token
        self.created_at = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_error_time = None
        self.is_valid = True
        self.scan_count = 0  # Counter for automatic rotation (every 5 scans)
        
    def increment_request(self):
        """Increment successful request counter"""
        self.request_count += 1
        
    def increment_scan(self):
        """Increment scan counter for automatic rotation"""
        self.scan_count += 1
        
    def needs_rotation(self, rotation_interval=5):
        """Check if this session needs rotation (every N scans)"""
        return self.scan_count >= rotation_interval
        
    def increment_error(self):
        """Increment error counter"""
        self.error_count += 1
        self.last_error_time = time.time()
        
        # Mark as invalid if too many errors (5+)
        if self.error_count >= 5:
            self.is_valid = False
            logger.warning(f"[TOKEN_POOL] Session {self.session_id} marked as invalid (5+ errors)")
    
    def get_age_seconds(self):
        """Get age of this session in seconds"""
        return time.time() - self.created_at
    
    def __repr__(self):
        return f"TokenSession(id={self.session_id}, requests={self.request_count}, errors={self.error_count}, age={self.get_age_seconds():.0f}s)"


class TokenPool:
    """
    Manages a pool of independent sessions with unique tokens.
    
    Features:
    - Pre-warming: Creates all tokens BEFORE workers start (fast startup!)
    - Unique User-Agent per session
    - Automatic invalid token removal
    - Thread-safe operations
    - Dynamic scaling (creates more tokens as needed)
    """
    
    def __init__(self, target_size=72, max_size=100, prewarm=True):
        """
        Initialize Token Pool.
        
        Args:
            target_size: Target number of tokens to maintain (default: 72 for 72 queries)
            max_size: Maximum tokens to create (default: 100)
            prewarm: If True, creates all tokens immediately (default: True)
        """
        self.target_size = target_size
        self.max_size = max_size
        self.sessions = []
        self.lock = threading.Lock()
        self.next_session_id = 1
        
        logger.info(f"[TOKEN_POOL] Initialized with target_size={target_size}, max_size={max_size}, prewarm={prewarm}")
        
        # Pre-warm pool if requested
        if prewarm:
            self._prewarm_pool()
    
    def _prewarm_pool(self):
        """
        Pre-warm pool by creating tokens PARALLELLY in background threads.
        This is FAST - creates 72 tokens in ~10 seconds instead of 60!
        """
        logger.info(f"[TOKEN_POOL] 🔥 Pre-warming pool: creating {self.target_size} tokens IN PARALLEL...")
        
        import proxies
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Recheck bad proxies before creating new token-proxy pairs
        logger.info(f"[TOKEN_POOL] 🔄 Rechecking bad proxies before creating token pool...")
        recovered = proxies.recheck_bad_proxies()
        if recovered > 0:
            logger.info(f"[TOKEN_POOL] 🎉 Recovered {recovered} proxies - now available for token-proxy pairs!")
        
        # Ensure proxies are loaded
        proxies.get_random_proxy()
        
        start_time = time.time()
        created = 0
        failed = 0
        
        def create_token_with_index(index):
            """Create single token - runs in separate thread"""
            try:
                # Small staggered delay to avoid simultaneous requests
                time.sleep(index * 0.1)  # 0.1s delay between each start
                
                proxy_dict = proxies.get_random_proxy()
                session = self._create_new_session_with_proxy(proxy_dict)
                return (index, session)
            except Exception as e:
                logger.error(f"[TOKEN_POOL] Error creating token #{index}: {e}")
                return (index, None)
        
        # Create tokens in parallel (10 at a time to avoid overload)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_token_with_index, i) for i in range(self.target_size)]
            
            for future in as_completed(futures):
                index, session = future.result()
                if session:
                    with self.lock:
                        self.sessions.append(session)
                    created += 1
                    logger.info(f"[TOKEN_POOL] ✅ Token {created}/{self.target_size} ready")
                else:
                    failed += 1
                    logger.warning(f"[TOKEN_POOL] ❌ Token {index+1} failed")
        
        elapsed = time.time() - start_time
        logger.info(f"[TOKEN_POOL] ✅ PARALLEL pre-warming complete: {created} tokens in {elapsed:.1f}s!")
        logger.info(f"[TOKEN_POOL] 🚀 That's {self.target_size/elapsed:.1f} tokens/sec (was 1.2 tokens/sec before)!")
    
    def _create_new_session_with_proxy(self, proxy_dict):
        """
        Create a new session with unique token, User-Agent, AND proxy.
        Used during pre-warming.
        
        Args:
            proxy_dict: Proxy configuration from proxies module
            
        Returns:
            TokenSession or None if creation failed
        """
        session_id = self.next_session_id
        self.next_session_id += 1
        
        try:
            # Create new session
            session = requests.Session()
            
            # Configure proxy if provided
            if proxy_dict:
                import proxies
                converted_proxy = proxies.convert_proxy_string_to_dict(proxy_dict)
                session.proxies.update(converted_proxy)
            
            # Select random User-Agent
            user_agent = random.choice(USER_AGENTS)
            
            # Set headers with unique User-Agent
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://www.vinted.de/",
                "Origin": "https://www.vinted.de",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": user_agent
            }
            
            # Add Chrome-specific headers if it's Chrome UA
            if "Chrome" in user_agent and "Edg" not in user_agent:
                headers.update({
                    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                })
            
            session.headers.update(headers)
            
            # Get access token from main page
            logger.debug(f"[TOKEN_POOL] Creating session #{session_id}...")
            response = session.get("https://www.vinted.de/", timeout=30)
            
            if response.status_code != 200:
                logger.error(f"[TOKEN_POOL] Failed to get main page for session #{session_id}: {response.status_code}")
                return None
            
            # Extract access_token_web from cookies
            access_token = None
            for cookie in session.cookies:
                if cookie.name == 'access_token_web':
                    access_token = cookie.value
                    break
            
            if not access_token:
                logger.error(f"[TOKEN_POOL] No access_token_web found in cookies for session #{session_id}")
                return None
            
            # Add Bearer authorization
            session.headers["Authorization"] = f"Bearer {access_token}"
            
            token_session = TokenSession(session_id, session, access_token, user_agent, proxy_dict)
            # Show UNIQUE part of token (middle chars) and full browser info
            token_preview = f"{access_token[:10]}...{access_token[-10:]}"  # First 10 + last 10 chars
            ua_short = user_agent[:80] if len(user_agent) <= 80 else user_agent[:77] + "..."
            proxy_display = f"{proxy_dict[:30]}..." if proxy_dict and len(str(proxy_dict)) > 30 else str(proxy_dict)
            logger.info(f"[TOKEN_POOL] ✅ Session #{session_id} | Token: {token_preview} | Proxy: {proxy_display} | UA: {ua_short}")
            
            return token_session
            
        except Exception as e:
            logger.error(f"[TOKEN_POOL] Error creating session #{session_id}: {e}")
            return None
    
    def _create_new_session(self):
        """
        Create a new session with unique token and User-Agent.
        
        Returns:
            TokenSession or None if creation failed
        """
        session_id = self.next_session_id
        self.next_session_id += 1
        
        try:
            # Create new session
            session = requests.Session()
            
            # Select random User-Agent
            user_agent = random.choice(USER_AGENTS)
            
            # Set headers with unique User-Agent
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://www.vinted.de/",
                "Origin": "https://www.vinted.de",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": user_agent
            }
            
            # Add Chrome-specific headers if it's Chrome UA
            if "Chrome" in user_agent and "Edg" not in user_agent:
                headers.update({
                    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                })
            
            session.headers.update(headers)
            
            # Get access token from main page
            logger.info(f"[TOKEN_POOL] Creating session #{session_id} with UA: {user_agent[:50]}...")
            response = session.get("https://www.vinted.de/", timeout=30)
            
            if response.status_code != 200:
                logger.error(f"[TOKEN_POOL] Failed to get main page for session #{session_id}: {response.status_code}")
                return None
            
            # Extract access_token_web from cookies
            access_token = None
            for cookie in session.cookies:
                if cookie.name == 'access_token_web':
                    access_token = cookie.value
                    break
            
            if not access_token:
                logger.error(f"[TOKEN_POOL] No access_token_web found in cookies for session #{session_id}")
                return None
            
            # Add Bearer authorization
            session.headers["Authorization"] = f"Bearer {access_token}"
            
            # Legacy mode - no proxy binding
            token_session = TokenSession(session_id, session, access_token, user_agent, proxy=None)
            # Show full browser info to see unique User-Agent
            ua_short = user_agent[:80] if len(user_agent) <= 80 else user_agent[:77] + "..."
            logger.info(f"[TOKEN_POOL] ✅ Session #{session_id} created (no proxy) | UA: {ua_short}")
            
            return token_session
            
        except Exception as e:
            logger.error(f"[TOKEN_POOL] Error creating session #{session_id}: {e}")
            return None
    
    def get_session_for_worker(self, worker_id):
        """
        Get or create a session for a specific worker.
        
        Args:
            worker_id: Unique worker identifier
            
        Returns:
            TokenSession
        """
        with self.lock:
            # 🔥 КРИТИЧНО: Создаем ПО ОДНОМУ токену для КАЖДОГО воркера!
            # Если воркеров больше чем токенов - создаем новые токены
            # Это гарантирует что каждый воркер получит УНИКАЛЬНЫЙ токен
            while len(self.sessions) <= worker_id and len(self.sessions) < self.max_size:
                logger.info(f"[TOKEN_POOL] Worker #{worker_id} needs token - creating session #{len(self.sessions) + 1}/{self.target_size}...")
                # 🔥 ВАЖНО: Используем метод С ПРОКСИ, иначе ban!
                import proxies
                proxy_dict = proxies.get_random_proxy()
                new_session = self._create_new_session_with_proxy(proxy_dict)
                if new_session:
                    self.sessions.append(new_session)
                    logger.info(f"[TOKEN_POOL] ✅ Created session #{new_session.session_id} for worker #{worker_id}")
                else:
                    logger.error(f"[TOKEN_POOL] ❌ Failed to create session for worker #{worker_id}")
                    break
            
            # If no sessions available, return None (worker will retry)
            if not self.sessions:
                logger.error(f"[TOKEN_POOL] No valid sessions available!")
                return None
            
            # 🔥 КРИТИЧНО: Каждый воркер получает СВОЙ токен по индексу
            # Worker 0 → Token 0, Worker 1 → Token 1, и т.д.
            session_idx = min(worker_id, len(self.sessions) - 1)
            session = self.sessions[session_idx]
            
            # 🔥 КРИТИЧНО: Если токен невалиден - ЗАМЕНЯЕМ его на новый НА МЕСТЕ!
            # Это сохраняет привязку worker_id → session_idx
            if not session.is_valid:
                logger.warning(f"[TOKEN_POOL] Worker #{worker_id} has INVALID token (session #{session.session_id}) - REPLACING on the spot!")
                import proxies
                proxy_dict = proxies.get_random_proxy()
                new_session = self._create_new_session_with_proxy(proxy_dict)
                if new_session:
                    # Заменяем невалидный токен НОВЫМ на том же индексе
                    self.sessions[session_idx] = new_session
                    session = new_session
                    logger.info(f"[TOKEN_POOL] ✅ Worker #{worker_id} got NEW token (session #{new_session.session_id}) at same index!")
                else:
                    logger.error(f"[TOKEN_POOL] ❌ Failed to create replacement token for worker #{worker_id}!")
                    # Оставляем старый невалидный токен - воркер попробует позже
            
            logger.debug(f"[TOKEN_POOL] Worker #{worker_id} → Session #{session.session_id} (UA: {session.user_agent[:30]}...)")
            return session
    
    def report_success(self, session):
        """Report successful request for a session"""
        with self.lock:
            if session and session in self.sessions:
                session.increment_request()
    
    def report_error(self, session):
        """Report error for a session"""
        with self.lock:
            if session and session in self.sessions:
                session.increment_error()
    
    def get_stats(self):
        """Get pool statistics"""
        with self.lock:
            valid_sessions = [s for s in self.sessions if s.is_valid]
            total_requests = sum(s.request_count for s in valid_sessions)
            total_errors = sum(s.error_count for s in valid_sessions)
            
            return {
                "total_sessions": len(self.sessions),
                "valid_sessions": len(valid_sessions),
                "target_size": self.target_size,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "user_agents": list(set(s.user_agent for s in valid_sessions))
            }
    
    def refresh_invalid_sessions(self):
        """Remove invalid sessions and create new ones"""
        with self.lock:
            before = len(self.sessions)
            self.sessions = [s for s in self.sessions if s.is_valid]
            after = len(self.sessions)
            
            removed = before - after
            if removed > 0:
                logger.info(f"[TOKEN_POOL] Removed {removed} invalid sessions")
    
    def create_fresh_pair(self, worker_index):
        """
        Create a completely fresh Token + Proxy pair for a worker.
        Used for:
        - Automatic rotation (every 5 scans)
        - Error recovery (immediate retry with new pair)
        
        Args:
            worker_index: Worker index to assign the new pair
            
        Returns:
            TokenSession: New session with Token + Proxy pair
        """
        logger.info(f"[TOKEN_POOL] 🔄 Creating fresh Token+Proxy pair for worker #{worker_index}...")
        
        import proxies
        # Periodically recheck bad proxies (every ~15th fresh pair creation)
        # This ensures bad proxies get rechecked during normal bot operation
        if worker_index % 15 == 0:
            logger.debug(f"[TOKEN_POOL] 🔄 Periodic recheck of bad proxies...")
            recovered = proxies.recheck_bad_proxies()
            if recovered > 0:
                logger.info(f"[TOKEN_POOL] 🎉 Recovered {recovered} proxies during periodic recheck!")
        
        proxy_dict = proxies.get_random_proxy()
        new_session = self._create_new_session_with_proxy(proxy_dict)
        
        if new_session:
            with self.lock:
                # Replace old session at worker_index
                if worker_index < len(self.sessions):
                    old_session = self.sessions[worker_index]
                    self.sessions[worker_index] = new_session
                    logger.info(f"[TOKEN_POOL] ✅ Worker #{worker_index}: Replaced session #{old_session.session_id} → #{new_session.session_id}")
                else:
                    # Worker index out of range - just append
                    self.sessions.append(new_session)
                    logger.info(f"[TOKEN_POOL] ✅ Worker #{worker_index}: Added new session #{new_session.session_id}")
            
            return new_session
        else:
            logger.error(f"[TOKEN_POOL] ❌ Failed to create fresh pair for worker #{worker_index}")
            return None


# Global token pool instance
_global_token_pool = None

def get_token_pool(target_size=72, prewarm=False):
    """Get or create global token pool instance"""
    global _global_token_pool
    if _global_token_pool is None:
        _global_token_pool = TokenPool(target_size=target_size, prewarm=prewarm)
    return _global_token_pool

