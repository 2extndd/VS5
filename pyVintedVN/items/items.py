from pyVintedVN.items.item import Item
from pyVintedVN.requester import requester
from urllib.parse import urlparse, parse_qsl
from requests.exceptions import HTTPError
from typing import List, Dict, Optional
from pyVintedVN.settings import Urls
import sys
import os

# Add the parent directory to sys.path to import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import get_logger

# Get logger for this module
logger = get_logger(__name__)


class Items:
    """
    A class for searching and retrieving items from Vinted.

    This class provides methods to search for items on Vinted using a search URL
    and to parse Vinted search URLs into API parameters.

    Example:
        >>> items = Items()
        >>> results = items.search("https://www.vinted.fr/catalog?search_text=shoes")
        
        >>> # Or with dedicated session:
        >>> items = Items(session=my_session)
        >>> results = items.search("https://www.vinted.fr/catalog?search_text=shoes")
    """
    
    def __init__(self, session=None):
        """
        Initialize Items class.
        
        Args:
            session: Optional requests.Session instance with Bearer token.
                     If not provided, uses global requester (legacy mode).
        """
        self.session = session

    def search(self, url: str, nbr_items: int = 20, page: int = 1,
               time: Optional[int] = None, json: bool = False):
        """
        Retrieve items from a given search URL on Vinted.

        Args:
            url (str): The URL of the search on Vinted.
            nbr_items (int, optional): Number of items to be returned. Defaults to 20.
            page (int, optional): Page number to be returned. Defaults to 1.
            time (int, optional): Timestamp to filter items by time. Defaults to None. Looks like it doesn't work though.
            json (bool, optional): Whether to return raw JSON data instead of Item objects.
                Defaults to False.

        Returns:
            List[Item] or tuple: A list of Item objects, or (response, status_code) tuple for HTTP errors.
        """
        # Extract the domain from the URL and set the locale
        locale = urlparse(url).netloc
        
        # Use dedicated session if provided, otherwise fall back to global requester
        if self.session:
            # Using dedicated session from token pool
            # Update locale-specific headers
            self.session.headers.update({
                "Host": locale,
                "Referer": f"https://{locale}/",
                "Origin": f"https://{locale}",
            })
        else:
            # Legacy mode: use global requester instance
            from pyVintedVN.requester import requester as requester_instance
            requester_instance.set_locale(locale)

        # Parse the URL to get the API parameters
        params = self.parse_url(url, nbr_items, page, time)

        # Construct the API URL
        api_url = f"https://{locale}{Urls.VINTED_API_URL}/{Urls.VINTED_PRODUCTS_ENDPOINT}"

        try:
            # Make the request using dedicated session or global requester
            response = None
            if self.session:
                # Using dedicated session from token pool
                # Proxy is already bound to this session - DON'T change it!
                # Token and Proxy live together as a pair

                # Make the request with dedicated session (proxy already configured)
                response = self.session.get(url=api_url, params=params, timeout=30, allow_redirects=True)

                # Increment API request counter
                try:
                    import db
                    db.increment_api_requests()
                    logger.debug(f"[API_COUNTER] ✅ API request counted (dedicated session)")
                except Exception as e:
                    logger.warning(f"[API_COUNTER] ⚠️ Failed to increment counter: {e}")
            else:
                # Legacy mode: use global requester
                from pyVintedVN.requester import requester as requester_instance
                response = requester_instance.get(url=api_url, params=params)

            # Check for HTTP errors before raising
            if response.status_code in (401, 403, 429):
                # Don't raise_for_status here - let caller handle it
                # But return the response and status code for error reporting
                return response, response.status_code

            response.raise_for_status()

            # Parse the response
            response_data = response.json()
            
            # Debug logs removed as requested
            
            items = response_data["items"]

            # Return either Item objects or raw JSON data
            if not json:
                item_objects = [Item(_item) for _item in items]
                return item_objects
            else:
                return items

        except HTTPError as err:
            raise err

    def parse_url(self, url: str, nbr_items: int = 20, page: int = 1,
                  time: Optional[int] = None) -> Dict:
        """
        Parse a Vinted search URL to get parameters for the API call.

        Args:
            url (str): The URL of the search on Vinted.
            nbr_items (int, optional): Number of items to be returned. Defaults to 20.
            page (int, optional): Page number to be returned. Defaults to 1.
            time (int, optional): Timestamp to filter items by time. Defaults to None.

        Returns:
            Dict: A dictionary of parameters for the Vinted API.
        """
        # Parse the query parameters from the URL
        queries = parse_qsl(urlparse(url).query)

        # Construct the parameters dictionary
        params = {
            "search_text": "+".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "search_text"])
            ),
            "video_game_platform_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "video_game_platform_ids[]"])
            ),
            "catalog_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "catalog[]"])
            ),
            "color_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "color_ids[]"])
            ),
            "brand_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "brand_ids[]"])
            ),
            "size_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "size_ids[]"])
            ),
            "material_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "material_ids[]"])
            ),
            "status_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "status_ids[]"])
            ),
            "country_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "country_ids[]"])
            ),
            "city_ids": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "city_ids[]"])
            ),
            "is_for_swap": ",".join(
                map(str, [1 for tpl in queries if tpl[0] == "disposal[]"])
            ),
            "currency": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "currency"])
            ),
            "price_to": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "price_to"])
            ),
            "price_from": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "price_from"])
            ),
            "page": page,
            "per_page": nbr_items,
            "order": ",".join(
                map(str, [tpl[1] for tpl in queries if tpl[0] == "order"])
            ),
            "time": time
        }

        return params

    # Aliases for backward compatibility
    parseUrl = parse_url
