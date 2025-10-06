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
    Represents a single session with unique token and User-Agent.
    """
    def __init__(self, session_id, session, access_token, user_agent):
        self.session_id = session_id
        self.session = session
        self.access_token = access_token
        self.user_agent = user_agent
        self.created_at = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_error_time = None
        self.is_valid = True
        
    def increment_request(self):
        """Increment successful request counter"""
        self.request_count += 1
        
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
        Pre-warm pool by creating all tokens upfront.
        This allows workers to start immediately without waiting for token creation.
        Creates tokens with small delays to avoid triggering rate limits.
        """
        logger.info(f"[TOKEN_POOL] 🔥 Pre-warming pool: creating {self.target_size} tokens...")
        
        import proxies
        # Ensure proxies are loaded
        proxies.get_random_proxy()
        
        start_time = time.time()
        created = 0
        failed = 0
        
        for i in range(self.target_size):
            # Get a random proxy for this token
            proxy_dict = proxies.get_random_proxy()
            
            session = self._create_new_session_with_proxy(proxy_dict)
            if session:
                with self.lock:
                    self.sessions.append(session)
                created += 1
                
                # Small delay between token requests (0.8s = 72 tokens in ~60 seconds)
                if i < self.target_size - 1:  # Don't delay after last token
                    time.sleep(0.8)
            else:
                failed += 1
                logger.warning(f"[TOKEN_POOL] Failed to create token {i+1}/{self.target_size}")
                # Wait a bit longer after failure
                time.sleep(2)
        
        elapsed = time.time() - start_time
        logger.info(f"[TOKEN_POOL] ✅ Pre-warming complete: {created} tokens created, {failed} failed in {elapsed:.1f}s")
        logger.info(f"[TOKEN_POOL] 🚀 Workers can now start IMMEDIATELY with ready tokens!")
    
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
            
            token_session = TokenSession(session_id, session, access_token, user_agent)
            logger.info(f"[TOKEN_POOL] ✅ Session #{session_id} | Token: {access_token[:20]}... | UA: {user_agent.split('(')[0].strip()[:25]}")
            
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
            
            token_session = TokenSession(session_id, session, access_token, user_agent)
            logger.info(f"[TOKEN_POOL] ✅ Session #{session_id} created | UA: {user_agent.split('(')[0].strip()[:30]}")
            
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
            # Remove invalid sessions
            self.sessions = [s for s in self.sessions if s.is_valid]
            
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
            # Если воркеров больше чем токенов - используем модуло
            session_idx = min(worker_id, len(self.sessions) - 1)
            session = self.sessions[session_idx]
            
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


# Global token pool instance
_global_token_pool = None

def get_token_pool(target_size=72, prewarm=False):
    """Get or create global token pool instance"""
    global _global_token_pool
    if _global_token_pool is None:
        _global_token_pool = TokenPool(target_size=target_size, prewarm=prewarm)
    return _global_token_pool

