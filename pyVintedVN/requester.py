import requests, os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import configuration_values as conf, proxies
from logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

class requester:
    def __init__(self, cookie=None, with_proxy=True, debug=False, headers=None):
        self.debug = debug
        if self.debug:
            logger.info(f"[DEBUG] Initializing requester (proxy: {with_proxy}, debug: {debug})")

        self.MAX_RETRIES = 5
        self.HEADER = headers if headers else conf.DEFAULT_HEADERS
        
        if self.debug:
            logger.info(f"[DEBUG] Using headers: {self.HEADER}")
            
        logger.debug(f"Initializing requester (proxy: {with_proxy}, debug: {debug})")
        logger.debug(f"Using headers: {self.HEADER}")

        self.session = requests.Session()
        self.session.headers.update(self.HEADER)

        # proxy
        proxy_configured = proxies.configure_proxy(self.session) if with_proxy else False
        if self.debug:
            if proxy_configured:
                logger.info(f"[DEBUG] Session initialized with proxy: {self.session.proxies}")
            else:
                logger.info(f"[DEBUG] Session initialized without proxy")
                
        if proxy_configured:
            logger.debug(f"Session initialized with proxy: {self.session.proxies}")
        else:
            logger.debug("Session initialized without proxy")

        # If cookies are required, set them from the db or from the parameter
        if cookie:
            self.set_cookies(cookie)
        else:
            self.set_cookies()

    def set_locale(self, locale):
        """
        Set the locale of the requester.
        Updates the authentication URL and headers to use the specified locale.
        
        Args:
            locale (str): The locale domain to use (e.g., 'www.vinted.fr', 'www.vinted.de')
        """
        if self.debug:
            logger.info(f"[DEBUG] Setting locale to: {locale}")
        logger.debug(f"Setting locale to: {locale}")
        
        # Update headers for the specific locale
        locale_headers = {
            "Host": f"{locale}",
            "Referer": f"https://{locale}/",
            "Origin": f"https://{locale}",
        }
        self.session.headers.update(locale_headers)
        
        if self.debug:
            logger.info(f"[DEBUG] Locale set to {locale}")
        logger.debug(f"Locale set to {locale}")

    def set_cookies(self, cookie=None):
        logger.debug("Setting up cookies")
        if self.debug:
            logger.info("[DEBUG] Setting up cookies")
            
        import db
        if cookie:
            self.session.cookies.update(cookie)
            if self.debug:
                logger.info(f"[DEBUG] Using provided cookies: {cookie}")
            logger.debug(f"Using provided cookies: {cookie}")
        else:
            cookie_db = db.get_parameter("cookie")
            if cookie_db:
                cookie = eval(cookie_db)
                self.session.cookies.update(cookie)
                if self.debug:
                    logger.info(f"[DEBUG] Using database cookies: {cookie}")
                logger.debug(f"Using database cookies: {cookie}")
            else:
                if self.debug:
                    logger.info("[DEBUG] No cookies found in database")
                logger.debug("No cookies found in database")

    def get(self, url, params=None):
        if self.debug:
            logger.info(f"[DEBUG] Making GET request to: {url}")
            if params:
                logger.info(f"[DEBUG] Request params: {params}")
                
        logger.debug(f"Making GET request to: {url}")
        if params:
            logger.debug(f"Request params: {params}")

        # proxy
        proxy_configured = proxies.configure_proxy(self.session)
        if self.debug:
            if proxy_configured:
                logger.info(f"[DEBUG] Using proxy for request: {self.session.proxies}")
            else:
                logger.info(f"[DEBUG] No proxy configured - direct connection")
        
        if proxy_configured:
            logger.debug(f"Using proxy for request: {self.session.proxies}")
        else:
            logger.debug("No proxy configured - direct connection")

        tried = 0
        new_session = False
        while tried < self.MAX_RETRIES:
            tried += 1
            with self.session.get(url, params=params) as response:
                if self.debug:
                    logger.info(f"[DEBUG] Request to {url} returned status {response.status_code}")
                    logger.info(f"[DEBUG] Response headers: {dict(response.headers)}")
                    if response.text:
                        logger.info(f"[DEBUG] Response text (first 500 chars): {response.text[:500]}")
                        
                logger.debug(f"Request to {url} returned status {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                if response.text:
                    logger.debug(f"Response text (first 500 chars): {response.text[:500]}")
                
                if response.status_code in (401, 404) and tried < self.MAX_RETRIES:
                    logger.info(f"Cookies invalid, retrying {tried}/{self.MAX_RETRIES}")
                    if self.debug:
                        logger.info(f"[DEBUG] Cookies invalid retrying {tried}/{self.MAX_RETRIES}")
                        logger.info(f"[DEBUG] Current cookies: {dict(self.session.cookies)}")
                    logger.debug(f"Cookies invalid retrying {tried}/{self.MAX_RETRIES}")
                    logger.debug(f"Current cookies: {dict(self.session.cookies)}")
                    self.set_cookies()
                elif response.status_code == 200:
                    return response
                elif tried == self.MAX_RETRIES:
                    # If we've reached max retries, return the last response
                    # even if it's not a 200 status code

                    # New try : if we still get a 401, we reset the session
                    if response.status_code in (401, 403) and not new_session:
                        new_session = True
                        self.session = requests.Session()
                        self.session.headers.update(self.HEADER)
                        # proxy
                        proxy_configured = proxies.configure_proxy(self.session)
                        if self.debug:
                            logger.info(f"[DEBUG] Session reset due to 401 error")
                            if proxy_configured:
                                logger.info(f"[DEBUG] New session using proxy: {self.session.proxies}")
                            else:
                                logger.info(f"[DEBUG] New session - no proxy configured")
                        tried = 0
                        continue
                    return response

        # This should only happen if the loop exits without returning
        return response

    def post(self, url, data=None, json_data=None):
        logger.debug(f"Making POST request to: {url}")
        if self.debug:
            logger.info(f"[DEBUG] Making POST request to: {url}")
            if data:
                logger.info(f"[DEBUG] POST data: {data}")
            if json_data:
                logger.info(f"[DEBUG] POST JSON: {json_data}")
                
        if data:
            logger.debug(f"POST data: {data}")
        if json_data:
            logger.debug(f"POST JSON: {json_data}")

        # proxy
        proxy_configured = proxies.configure_proxy(self.session)
        if self.debug:
            if proxy_configured:
                logger.info(f"[DEBUG] Using proxy for POST: {self.session.proxies}")
            else:
                logger.info(f"[DEBUG] No proxy configured for POST - direct connection")
                
        if proxy_configured:
            logger.debug(f"Using proxy for POST: {self.session.proxies}")
        else:
            logger.debug("No proxy configured for POST - direct connection")

        tried = 0
        while tried < self.MAX_RETRIES:
            tried += 1
            if json_data:
                response = self.session.post(url, json=json_data)
            else:
                response = self.session.post(url, data=data)
                
            if self.debug:
                logger.info(f"[DEBUG] POST to {url} returned status {response.status_code}")
                logger.info(f"[DEBUG] POST response headers: {dict(response.headers)}")
                if response.text:
                    logger.info(f"[DEBUG] POST response text (first 500 chars): {response.text[:500]}")
                    
            logger.debug(f"POST to {url} returned status {response.status_code}")
            logger.debug(f"POST response headers: {dict(response.headers)}")
            if response.text:
                logger.debug(f"POST response text (first 500 chars): {response.text[:500]}")

            if response.status_code in (401, 404) and tried < self.MAX_RETRIES:
                logger.info(f"POST: Cookies invalid, retrying {tried}/{self.MAX_RETRIES}")
                if self.debug:
                    logger.info(f"[DEBUG] POST: Cookies invalid retrying {tried}/{self.MAX_RETRIES}")
                    logger.info(f"[DEBUG] POST: Current cookies: {dict(self.session.cookies)}")
                logger.debug(f"POST: Cookies invalid retrying {tried}/{self.MAX_RETRIES}")
                logger.debug(f"POST: Current cookies: {dict(self.session.cookies)}")
                self.set_cookies()
            elif response.status_code == 200:
                return response
            elif tried == self.MAX_RETRIES:
                return response

        return response# Force cache refresh

# Singleton instance of the requester class for backward compatibility
requester = requester()
