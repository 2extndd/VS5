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
    """
    
    def __init__(self, requester=None):
        """
        Initialize Items with a dedicated requester instance.
        
        Args:
            requester: Dedicated requester instance (if None, uses global singleton)
        """
        if requester is not None:
            self.requester = requester
            logger.info("[ITEMS] Using dedicated requester instance (independent proxy)")
        else:
            # Fallback to global singleton for backward compatibility
            from pyVintedVN.requester import requester as requester_instance
            self.requester = requester_instance
            logger.info("[ITEMS] Using global requester instance (shared)")

    def search(self, url: str, nbr_items: int = 20, page: int = 1,
               time: Optional[int] = None, json: bool = False) -> List[Item]:
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
            List[Item]: A list of Item objects.

        Raises:
            HTTPError: If the request to the Vinted API fails.
        """
        # Extract the domain from the URL and set the locale
        locale = urlparse(url).netloc
        
        # Use THIS instance's dedicated requester (not global!)
        self.requester.set_locale(locale)

        # Parse the URL to get the API parameters
        params = self.parse_url(url, nbr_items, page, time)

        # Construct the API URL
        api_url = f"https://{locale}{Urls.VINTED_API_URL}/{Urls.VINTED_PRODUCTS_ENDPOINT}"

        try:
            # Make the request using THIS instance's dedicated requester
            response = self.requester.get(url=api_url, params=params)
            response.raise_for_status()

            # Parse the response
            response_data = response.json()
            
            # Debug logs
            logger.info(f"[DEBUG] Items API response status: {response.status_code}")
            logger.info(f"[DEBUG] API URL: {api_url}")
            logger.info(f"[DEBUG] API params: {params}")
            logger.info(f"[DEBUG] Response JSON keys: {list(response_data.keys()) if response_data else 'None'}")
            if 'items' in response_data:
                logger.info(f"[DEBUG] Number of items in API response: {len(response_data['items'])}")
                if response_data['items']:
                    first_item = response_data['items'][0]
                    logger.info(f"[DEBUG] First item ID: {first_item.get('id', 'Unknown')}")
                    logger.info(f"[DEBUG] First item title: {first_item.get('title', 'Unknown')}")
            else:
                logger.info(f"[DEBUG] No 'items' key in API response")
                logger.info(f"[DEBUG] Full API response: {response_data}")
            
            items = response_data["items"]

            # Return either Item objects or raw JSON data
            if not json:
                item_objects = [Item(_item) for _item in items]
                logger.info(f"[DEBUG] Created {len(item_objects)} Item objects from API response")
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
