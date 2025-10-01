import db, configuration_values, requests
from pyVintedVN import Vinted, requester
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from logger import get_logger
from performance_profiler import get_profiler
import time

# Get logger for this module
logger = get_logger(__name__)
profiler = get_profiler()


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


def process_items(queue):
    """
    Process all queries from the database, search for items, and put them in the queue.
    Uses the global items_queue by default, but can accept a custom queue for backward compatibility.

    Args:
        queue (Queue, optional): The queue to put the items in. Defaults to the global items_queue.

    Returns:
        None
    """
    try:
        # Start total cycle timer
        cycle_start = time.time()
        profiler.start_timer("total_cycle_time")
        
        logger.info(f"[DEBUG] process_items called - starting execution")
        logger.info(f"[PERF] 🚀 Starting new scraping cycle at {time.time()}")
        
        # Get database statistics for debugging
        profiler.start_timer("db_get_stats")
        db_stats = db.get_database_stats()
        profiler.end_timer("db_get_stats")
        logger.info(f"[DEBUG] Database statistics: {db_stats}")
        
        profiler.start_timer("db_get_queries")
        all_queries = db.get_queries()
        profiler.end_timer("db_get_queries")
        logger.info(f"[DEBUG] Got {len(all_queries)} queries from database")

        # Initialize Vinted
        vinted = Vinted()
        
        # Enable debug mode for troubleshooting
        from pyVintedVN.requester import requester
        requester.debug = True
        logger.info("Enabled debug mode for Vinted requests")

        # Get the number of items per query from the database
        items_per_query_param = db.get_parameter("items_per_query")
        items_per_query = int(items_per_query_param) if items_per_query_param else 20

        # for each keyword we parse data
        for query in all_queries:
            profiler.start_timer(f"query_{query[0]}_total")
            logger.info(f"[DEBUG] Calling vinted.items.search for query: {query[1]}")
            logger.info(f"[DEBUG] vinted.items type: {type(vinted.items)}")
            logger.info(f"[DEBUG] vinted.items.search method: {vinted.items.search}")
            
            # Measure API call time
            profiler.start_timer(f"query_{query[0]}_api_call")
            all_items = vinted.items.search(query[1], nbr_items=items_per_query)
            api_time = profiler.end_timer(f"query_{query[0]}_api_call")
            profiler.add_to_stats('api_request_to_response', api_time)
            
            # Debug: log info about found items
            logger.info(f"[DEBUG] *** CORE.PY *** Found {len(all_items)} total items for query")
            logger.info(f"[DEBUG] all_items type: {type(all_items)}")
            if all_items:
                first_item = all_items[0]
                logger.info(f"[DEBUG] First item type: {type(first_item)}")
                logger.info(f"[DEBUG] First item: {first_item}")
                try:
                    logger.info(f"[DEBUG] First item age: {(first_item.created_at_ts).isoformat()}")
                    logger.info(f"[DEBUG] Item is_new_item(60): {first_item.is_new_item(60)}")
                except Exception as e:
                    logger.info(f"[DEBUG] Error accessing item attributes: {e}")
            else:
                logger.info(f"[DEBUG] *** NO ITEMS RETURNED FROM SEARCH ***")
            
            # TEMPORARILY DISABLE TIME FILTER - accept all items but check for duplicates
            data = all_items  # Accept all items for now
            logger.info(f"[DEBUG] Putting {len(data)} items into queue for query_id {query[0]} (queue id: {id(queue)})")
            queue.put((data, query[0]))
            logger.info(f"[DEBUG] Successfully put items into queue (queue id: {id(queue)})")
            logger.info(f"Scraped {len(data)} items for query: {query[1]}")
            
            # End query timer
            profiler.end_timer(f"query_{query[0]}_total")
        
        # End total cycle timer and show summary
        total_cycle_time = profiler.end_timer("total_cycle_time")
        logger.info(f"[PERF] 🏁 Cycle completed in {total_cycle_time:.3f}s")
        
        # Log performance summary
        profiler.log_summary()
        
        # Reset current metrics for next cycle
        profiler.reset_current()
            
    except Exception as e:
        logger.error(f"[CRITICAL ERROR] process_items failed: {e}")
        import traceback
        logger.error(f"[CRITICAL ERROR] Traceback: {traceback.format_exc()}")
        
        # Log performance even on error
        try:
            profiler.log_summary()
        except:
            pass


def clear_item_queue(items_queue, new_items_queue):
    """
    Process items from the items_queue.
    This function is scheduled to run frequently.
    """
    logger.info(f"[DEBUG] clear_item_queue called - queue empty: {items_queue.empty()} (queue id: {id(items_queue)})")
    if not items_queue.empty():
        logger.info(f"[DEBUG] Found items in queue! Getting them...")
        data, query_id = items_queue.get()
        logger.info(f"[DEBUG] Got {len(data)} items from queue for query_id {query_id}")
        logger.info(f"[DEBUG] Starting to process {len(data)} items...")
        for item in reversed(data):
            logger.info(f"[DEBUG] Processing item {item.id}: {item.title[:50]}...")

            # Check if item already exists in database
            profiler.start_timer(f"item_{item.id}_db_check")
            is_duplicate = db.is_item_in_db_by_id(item.id)
            db_check_time = profiler.end_timer(f"item_{item.id}_db_check")
            profiler.add_to_stats('db_check_time', db_check_time)
            
            if is_duplicate:
                logger.info(f"[DEBUG] Item {item.id} already exists in database, skipping...")
                continue
                
            # TEMPORARILY DISABLE TIME FILTER - accept all items but check for duplicates
            if True:  # Accept all items for now
                profiler.start_timer(f"item_{item.id}_processing")
                logger.info(f"[DEBUG] Creating message for item {item.id}...")
                try:
                    # We create the message with conditional size display
                    if item.size_title and item.size_title.strip():
                        # Format message with size
                        content = f"<b>{item.title}</b>\n<b>💶{str(item.price)} {item.currency}</b>\n⛓️ {item.size_title}\n{item.brand_title}"
                    else:
                        # Format message without size line
                        content = f"<b>{item.title}</b>\n<b>💶{str(item.price)} {item.currency}</b>\n{item.brand_title}"
                    
                    # Add invisible image link if photo exists
                    if item.photo:
                        content += f"\n<a href='{item.photo}'>&#8205;</a>"
                    logger.info(f"[DEBUG] Message created successfully for item {item.id}")
                    
                    # Get thread_id for this query
                    thread_id = None
                    try:
                        # Get query details to extract thread_id
                        current_query = next((q for q in db.get_queries() if q[0] == query_id), None)
                        if current_query and len(current_query) > 4:
                            thread_id = current_query[4]  # thread_id is the 5th element (index 4)
                    except Exception as e:
                        logger.warning(f"Could not get thread_id for query {query_id}: {e}")
                    
                    # add the item to the queue with thread_id and photo_url
                    logger.info(f"[DEBUG] Adding item to queue: {item.title} (thread_id: {thread_id}, photo: {item.photo})")
                    new_items_queue.put((content, item.url, "Open Vinted", None, None, thread_id, item.photo))
                    logger.info(f"[DEBUG] Item added to new_items_queue successfully")
                    
                    # Add the item to the db
                    logger.info(f"[DEBUG] Adding item to database: {item.id}")
                    found_at = time.time()  # Record when bot found this item
                    
                    # Calculate and log item discovery latency
                    item_latency = profiler.calculate_item_latency(item.raw_timestamp, found_at)
                    profiler.add_to_stats('total_latency', item_latency)
                    
                    profiler.start_timer(f"item_{item.id}_db_insert")
                    db.add_item_to_db(id=item.id, title=item.title, query_id=query_id, price=item.price, 
                                      timestamp=item.raw_timestamp, photo_url=item.photo, currency=item.currency, 
                                      brand_title=item.brand_title, found_at=found_at)
                    db_insert_time = profiler.end_timer(f"item_{item.id}_db_insert")
                    profiler.add_to_stats('db_insert_time', db_insert_time)
                    
                    logger.info(f"[DEBUG] Item {item.id} successfully added to database!")
                    
                    # End item processing timer
                    item_proc_time = profiler.end_timer(f"item_{item.id}_processing")
                    logger.info(f"[PERF] ⚡ Item {item.id} total processing: {item_proc_time:.3f}s")
                    
                    # Update the query's last_found timestamp
                    logger.info(f"[DEBUG] Updating last_found for query {query_id}")
                    db.update_query_last_found(query_id, item.raw_timestamp)
                    logger.info(f"[DEBUG] Query {query_id} last_found updated!")
                    
                except Exception as e:
                    logger.error(f"[ERROR] Failed to process item {item.id}: {e}")
                    import traceback
                    logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")


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
