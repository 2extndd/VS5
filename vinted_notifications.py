import multiprocessing, time, core, os, db, configuration_values
from apscheduler.schedulers.background import BackgroundScheduler
from logger import get_logger
# RSS functionality removed
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

    # Test if core.process_items is callable
    logger.info(f"[DEBUG] core.process_items type: {type(core.process_items)}")
    logger.info(f"[DEBUG] core.process_items callable: {callable(core.process_items)}")
    
    scraper_scheduler = BackgroundScheduler()
    logger.info("[DEBUG] Created BackgroundScheduler")
    
    try:
        scraper_scheduler.add_job(core.process_items, 'interval', seconds=current_query_refresh_delay, args=[items_queue],
                                  name="scraper")
        logger.info("[DEBUG] Successfully added job to scheduler")
    except Exception as e:
        logger.error(f"[ERROR] Failed to add job to scheduler: {e}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        return
    
    logger.info("[DEBUG] Starting scheduler...")
    try:
        scraper_scheduler.start()
        logger.info("[DEBUG] Scheduler started! Entering main loop...")
    except Exception as e:
        logger.error(f"[ERROR] Failed to start scheduler: {e}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        return
    
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


def dispatcher_function(input_queue, telegram_queue):
    logger.info("Dispatcher process started")
    try:
        while True:
            # Get from input queue
            item = input_queue.get()
            # RSS functionality removed
            #
            telegram_queue.put(item)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dispatcher process stopped")
    except Exception as e:
        logger.error(f"Error in dispatcher process: {e}", exc_info=True)


def telegram_bot_process(queue):
    logger.info("Telegram bot process started")
    try:
        # Import LeRobot
        from telegram_bot_plugin.telegram_bot import LeRobot
        # Create and start the bot - LeRobot handles its own asyncio loop
        logger.info("Creating LeRobot instance...")
        bot = LeRobot(queue)
        logger.info("LeRobot created successfully and should be running!")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Telegram bot process stopped")
    except Exception as e:
        logger.error(f"Error in telegram bot process: {e}", exc_info=True)
        import traceback
        logger.error(f"Telegram bot traceback: {traceback.format_exc()}")


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


def monitor_processes(items_queue, telegram_queue):
    # Check if the query refresh delay has changed
    check_refresh_delay(items_queue)

    # Monitor processes are handled by the main scheduler now
    pass


def plugin_checker():
    # Get telegram enable status
    telegram_enabled = db.get_parameter('telegram_enabled') or 'False'
    logger.info("Telegram enabled: {}".format(telegram_enabled))
    # RSS functionality removed

    # Force Telegram bot to be enabled by default (Railway production environment)
    logger.info("Forcing Telegram bot to be enabled for production")
    db.set_parameter('telegram_enabled', 'True')
    db.set_parameter('telegram_process_running', 'True')
    
    # RSS removed


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
        
        # Run priority query system migration (safe to run multiple times)
        logger.info("Running priority query system migration...")
        if db.run_priority_migration():
            logger.info("✅ Priority query system migration completed successfully")
        else:
            logger.warning("⚠️ Priority query system migration failed (may already exist)")
        
        # Reset API requests counter on bot start
        logger.info("Resetting API requests counter...")
        db.reset_api_requests()
        logger.info("API requests counter reset")
        
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
    # RSS queue removed
    telegram_queue = manager.Queue()
    logger.info("[DEBUG] Queues created successfully!")

    # RAILWAY FIX: Use single process with threads instead of multiprocessing
    logger.info("[DEBUG] RAILWAY MODE: Starting single-process architecture...")
    
    # Get refresh delay from Web UI configuration
    query_refresh_delay_param = db.get_parameter("query_refresh_delay")
    current_query_refresh_delay = int(query_refresh_delay_param) if query_refresh_delay_param else 15
    logger.info(f"[DEBUG] Query refresh delay from Web UI: {current_query_refresh_delay} seconds")
    
    # Start INDEPENDENT continuous workers for each query (NO SCHEDULER!)
    logger.info("[DEBUG] Starting INDEPENDENT workers for each query...")
    logger.info(f"[DEBUG] Each query will scan every {current_query_refresh_delay} seconds in PARALLEL")
    
    # Get number of queries to show in logs
    all_queries_count = len(db.get_queries())
    logger.info(f"[DEBUG] 📊 Total queries in DB: {all_queries_count}")
    logger.info(f"[DEBUG] 📊 Expected workers: {all_queries_count}")
    logger.info(f"[DEBUG] 📊 Expected API requests per cycle: {all_queries_count}")
    logger.info(f"[DEBUG] 📊 Refresh delay: {current_query_refresh_delay}s")
    logger.info(f"[DEBUG] 📊 Expected requests per minute: ~{int(60 / current_query_refresh_delay * all_queries_count)}")
    
    workers_executor = core.start_continuous_workers(items_queue)
    if workers_executor:
        logger.info(f"[DEBUG] ✅ Independent workers started successfully!")
        logger.info(f"[DEBUG] ✅ {all_queries_count} workers are now running in parallel!")
    else:
        logger.error(f"[DEBUG] ❌ Failed to start independent workers!")
    
    # Start item processor scheduler - THIS WAS MISSING!
    logger.info("[DEBUG] Starting item processor scheduler...")
    processor_scheduler = BackgroundScheduler()
    # Ускоряем обработку очереди с 1 сек до 0.1 сек для мгновенной отправки
    processor_scheduler.add_job(core.clear_item_queue, 'interval', seconds=0.1, 
                               args=[items_queue, new_items_queue], name="item_processor")
    processor_scheduler.start()
    logger.info("[DEBUG] Item processor scheduler started (0.1s interval for instant processing)!")
    
    # Start monitor scheduler  
    monitor_scheduler = BackgroundScheduler()
    monitor_scheduler.add_job(monitor_processes, 'interval', seconds=5, 
                             args=[items_queue, telegram_queue], name="process_monitor")
    monitor_scheduler.start()
    logger.info("[DEBUG] Monitor scheduler started!")

    # Start SIMPLE Telegram sender instead of complex LeRobot
    logger.info("[DEBUG] Starting SIMPLE Telegram sender...")
    try:
        from simple_telegram_worker import start_simple_telegram_sender
        telegram_sender = start_simple_telegram_sender(new_items_queue)
        if telegram_sender:
            logger.info("[DEBUG] ✅ SIMPLE Telegram sender started successfully!")
        else:
            logger.error("[DEBUG] ❌ Failed to start SIMPLE Telegram sender")
    except Exception as e:
        logger.error(f"[DEBUG] ❌ Error starting SIMPLE Telegram sender: {e}")
        import traceback
        logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")

    # Start Web UI in the main process
    logger.info("[DEBUG] Starting Web UI in main process...")
    port = int(os.environ.get('PORT', configuration_values.WEB_UI_PORT))
    logger.info(f"Web UI starting on port {port}")
    
    # Import and start web UI directly
    from web_ui_plugin.web_ui import app
    logger.info("[DEBUG] Web UI app imported, starting server...")
    
    try:
        # Start schedulers in threads before starting Flask
        logger.info("[DEBUG] All systems started, now starting Flask server...")
        logger.info(f"[DEBUG] Independent workers: {workers_executor is not None}")
        logger.info(f"[DEBUG] Processor scheduler running: {processor_scheduler.running}")
        logger.info(f"[DEBUG] Monitor scheduler running: {monitor_scheduler.running}")
        
        # This will block and serve the web UI
        # Disable werkzeug logs to reduce log spam
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)  # Only show errors, not every HTTP request
        
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        logger.info("Main process interrupted")
        if workers_executor:
            workers_executor.shutdown(wait=False)
        processor_scheduler.shutdown()
        monitor_scheduler.shutdown()
        logger.info("All systems stopped")
