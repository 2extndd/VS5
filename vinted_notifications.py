import multiprocessing, time, core, os, db, configuration_values
from apscheduler.schedulers.background import BackgroundScheduler
from logger import get_logger
from rss_feed_plugin.rss_feed import rss_feed_process
from web_ui_plugin.web_ui import web_ui_process

# Get logger for this module
logger = get_logger(__name__)

# Global process references
current_query_refresh_delay = None

def scraper_process(items_queue):
    logger.info("[DEBUG] Scraper process function called!")
    logger.info("Scrape process started")
    logger.info(f"[DEBUG] Queue object received: {items_queue}")

    # Get the query refresh delay from the database
    query_refresh_delay_param = db.get_parameter("query_refresh_delay")
    current_query_refresh_delay = int(query_refresh_delay_param) if query_refresh_delay_param else 60
    logger.info(f"Using query refresh delay of {current_query_refresh_delay} seconds")

    scraper_scheduler = BackgroundScheduler()
    scraper_scheduler.add_job(core.process_items, 'interval', seconds=current_query_refresh_delay, args=[items_queue],
                              name="scraper")
    logger.info("[DEBUG] Starting scheduler...")
    scraper_scheduler.start()
    logger.info("[DEBUG] Scheduler started! Entering main loop...")
    try:
        # Keep the process running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scraper_scheduler.shutdown()
        logger.info("Scrape process stopped")


def item_extractor(items_queue, new_items_queue):
    logger.info("Item extractor process started")
    logger.info("[DEBUG] Item extractor process started")
    try:
        loop_count = 0
        while True:
            # Check if there's an item in the queue
            core.clear_item_queue(items_queue, new_items_queue)
            loop_count += 1
            if loop_count % 100 == 0:  # Log every 10 seconds (100 * 0.1s)
                logger.info(f"[DEBUG] Item extractor loop count: {loop_count}")
            time.sleep(0.1)  # Small sleep to prevent high CPU usage
    except (KeyboardInterrupt, SystemExit):
        logger.info("Item extractor process stopped")
    except Exception as e:
        logger.error(f"Critical error in item extractor process: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


def dispatcher_function(input_queue, rss_queue, telegram_queue):
    logger.info("Dispatcher process started")
    try:
        while True:
            # Get from input queue
            item = input_queue.get()
            # Send to RSS queue
            rss_queue.put(item)
            #
            telegram_queue.put(item)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dispatcher process stopped")
    except Exception as e:
        logger.error(f"Error in dispatcher process: {e}", exc_info=True)


def telegram_bot_process(queue):
    logger.info("Telegram bot process started")
    import asyncio
    try:
        # Import LeRobot
        from telegram_bot_plugin.telegram_bot import LeRobot
        # The bot will run with app.run_polling() which is already in the module
        asyncio.run(LeRobot(queue))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Telegram bot process stopped")
    except Exception as e:
        logger.error(f"Error in telegram bot process: {e}", exc_info=True)


def check_refresh_delay(items_queue):
    """Check if the query refresh delay has changed and update the scheduler if needed"""
    global current_query_refresh_delay

    # Get the current value from the database
    try:
        query_refresh_delay_param = db.get_parameter("query_refresh_delay")
        new_delay = int(query_refresh_delay_param) if query_refresh_delay_param else 60

        # If the delay has changed, update the scheduler
        if new_delay != current_query_refresh_delay:
            logger.info(f"Query refresh delay changed from {current_query_refresh_delay} to {new_delay} seconds")

            # Update the global variable
            current_query_refresh_delay = new_delay

            logger.info(f"Query refresh delay updated to {new_delay} seconds")
    except Exception as e:
        logger.error(f"Error updating refresh delay: {e}", exc_info=True)


def monitor_processes(items_queue, telegram_queue, rss_queue):
    # Check if the query refresh delay has changed
    check_refresh_delay(items_queue)

    # Monitor processes are handled by the main scheduler now
    pass


def plugin_checker():
    # Get telegram and rss enable status
    telegram_enabled = db.get_parameter('telegram_enabled') or 'False'
    logger.info("Telegram enabled: {}".format(telegram_enabled))
    rss_enabled = db.get_parameter('rss_enabled') or 'False'
    logger.info("RSS enabled: {}".format(rss_enabled))

    # Reset process status at startup
    db.set_parameter('telegram_process_running', telegram_enabled)
    db.set_parameter('rss_process_running', rss_enabled)


if __name__ == "__main__":
    # Starting sequence - FORCE DATABASE INITIALIZATION
    logger.info("=== STARTING VINTED NOTIFICATIONS BOT ===")
    
    try:
        # Db check - works with both SQLite and PostgreSQL
        logger.info("Getting database connection...")
        conn, db_type = db.get_db_connection()
        conn.close()
        
        logger.info(f"Database type detected: {db_type}")
        logger.info(f"Using database type: {db_type}")
        
        # ALWAYS initialize database for PostgreSQL to ensure tables exist
        if db_type == 'postgresql':
            logger.info("PostgreSQL detected - forcing database initialization...")
            logger.info("PostgreSQL detected - forcing database initialization...")
            db.create_or_update_db("initial_db.sql")
            logger.info("PostgreSQL database initialization completed")
            logger.info("PostgreSQL database initialization completed")
        else:
            # SQLite logic
            if not os.path.exists("./vinted_notifications.db"):
                logger.info("SQLite database file not found - creating...")
                logger.info("SQLite database file not found - creating...")
                db.create_or_update_db("initial_db.sql")
                logger.info("SQLite database created successfully")
            else:
                logger.info("SQLite database file exists - checking for migrations...")
                # Run migrations for existing database
                current_version = db.get_parameter('version')
                if current_version:
                    # Check if there is a file that starts with the current version in the migrations folder
                    migration_files = [f for f in os.listdir('migrations')]
                    while True:
                        migration_file = next((f for f in migration_files if f.startswith(current_version)), None)
                        if migration_file:
                            logger.info(f"Running migration: {migration_file}")
                            db.create_or_update_db("./migrations/" + migration_file)
                            # Increment the version
                            current_version = db.get_parameter('version')
                        else:
                            break
                else:
                    # No version found, database might be empty - try to initialize
                    logger.info("No version parameter found, initializing database...")
                    db.create_or_update_db("initial_db.sql")
                    logger.info("Database initialized successfully")
        
        logger.info("Database initialization phase completed")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR during database initialization: {e}")
        logger.error(f"CRITICAL ERROR during database initialization: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

    # Plugin checker
    plugin_checker()

    logger.info("[DEBUG] Starting to create queues...")
    # Create a shared queue using Manager for better cross-platform compatibility
    manager = multiprocessing.Manager()
    items_queue = manager.Queue()
    new_items_queue = manager.Queue()
    rss_queue = manager.Queue()
    telegram_queue = manager.Queue()
    logger.info("[DEBUG] Queues created successfully!")

    # 1. Create and start the scrape process
    # This process will scrape items and put them in the items_queue
    logger.info("[DEBUG] Creating scraper process...")
    query_refresh_delay_param = db.get_parameter("query_refresh_delay")
    current_query_refresh_delay = int(query_refresh_delay_param) if query_refresh_delay_param else 60
    logger.info(f"[DEBUG] Query refresh delay: {current_query_refresh_delay}")
    scraper_proc = multiprocessing.Process(target=scraper_process, args=(items_queue,))
    logger.info("[DEBUG] Starting scraper process...")
    scraper_proc.start()
    logger.info("[DEBUG] Scraper process started!")

    # 2. Create the item extractor process
    # This process will extract items from the items_queue and put them in the new_items_queue
    logger.info("[DEBUG] Creating item extractor process...")
    item_extractor_process = multiprocessing.Process(target=item_extractor, args=(items_queue, new_items_queue))
    logger.info("[DEBUG] Starting item extractor process...")
    item_extractor_process.start()
    logger.info("[DEBUG] Item extractor process started!")

    # 3. Create the dispatcher process
    # This process will handle the new items and send them to the enabled services
    logger.info("[DEBUG] Creating dispatcher process...")
    dispatcher_process = multiprocessing.Process(target=dispatcher_function,
                                                 args=(new_items_queue, rss_queue, telegram_queue,))
    logger.info("[DEBUG] Starting dispatcher process...")
    dispatcher_process.start()
    logger.info("[DEBUG] Dispatcher process started!")

    # 4. Create and start the Telegram bot process
    # This process will handle telegram messages
    logger.info("[DEBUG] Creating telegram bot process...")
    telegram_bot_process_instance = multiprocessing.Process(target=telegram_bot_process, args=(telegram_queue,))
    logger.info("[DEBUG] Starting telegram bot process...")
    telegram_bot_process_instance.start()
    logger.info("[DEBUG] Telegram bot process started!")

    # 5. Set up a scheduler to monitor processes
    # This will check the process status in the database and start/stop processes as needed
    monitor_scheduler = BackgroundScheduler()
    monitor_scheduler.add_job(monitor_processes, 'interval', seconds=5, args=[items_queue, telegram_queue, rss_queue],
                              name="process_monitor")
    monitor_scheduler.start()

    # 6. Create and start the Web UI process
    # This process will provide a web interface to control the application
    logger.info("[DEBUG] Creating web UI process...")
    web_ui_process_instance = multiprocessing.Process(target=web_ui_process)
    logger.info("[DEBUG] Starting web UI process...")
    web_ui_process_instance.start()
    logger.info("[DEBUG] Web UI process started!")
    
    # Port will be logged by the web UI process itself
    port = int(os.environ.get('PORT', configuration_values.WEB_UI_PORT))
    logger.info(f"Web UI starting on port {port}")


    try:
        # Wait for processes to finish (which they won't unless interrupted)
        scraper_proc.join()
        item_extractor_process.join()
        dispatcher_process.join()
        telegram_bot_process_instance.join()
        web_ui_process_instance.join()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Main process interrupted")

        # Shutdown the monitor scheduler
        monitor_scheduler.shutdown()

        # Terminate all processes
        scraper_proc.terminate()
        item_extractor_process.terminate()
        dispatcher_process.terminate()
        telegram_bot_process_instance.terminate()
        # Terminate web UI process
        web_ui_process_instance.terminate()

        # Wait for all processes to terminate
        scraper_proc.join()
        item_extractor_process.join()
        dispatcher_process.join()
        telegram_bot_process_instance.join()
        web_ui_process_instance.join()

        logger.info("All processes terminated")
