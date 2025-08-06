from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import RetryAfter
import db, core, asyncio
from logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ver = db.get_parameter("version")
        await update.message.reply_text(
            f'Hello {update.effective_user.first_name}! Vinted-Notifications is running under version {ver}.\n')
    except Exception as e:
        logger.error(f"Error in hello command: {str(e)}", exc_info=True)
        try:
            await update.message.reply_text('An error occurred. Please try again later.')
        except:
            pass


class LeRobot:
    def __init__(self, queue):
        from telegram import Bot
        from telegram.ext import ApplicationBuilder, CommandHandler

        try:

            self.bot = Bot(db.get_parameter("telegram_token"))
            self.app = ApplicationBuilder().token(db.get_parameter("telegram_token")).build()

            # Create the item queue to send to telegram
            self.new_items_queue = queue

            # Handler verify if bot is running
            self.app.add_handler(CommandHandler("hello", hello))
            # Telegram Mini App handler
            self.app.add_handler(CommandHandler("app", self.open_web_app))
            # Keyword handlers
            self.app.add_handler(CommandHandler("add_query", self.add_query))
            self.app.add_handler(CommandHandler("remove_query", self.remove_query))
            self.app.add_handler(CommandHandler("queries", self.queries))
            # Allowlist handlers
            self.app.add_handler(CommandHandler("clear_allowlist", self.clear_allowlist))
            self.app.add_handler(CommandHandler("add_country", self.add_country))
            self.app.add_handler(CommandHandler("remove_country", self.remove_country))
            self.app.add_handler(CommandHandler("allowlist", self.allowlist))
            # Thread ID handler
            self.app.add_handler(CommandHandler("thread_id", self.get_thread_id))

            # TODO : Help command

            # TODO : Manage removals after current items have been processed.

            job_queue = self.app.job_queue
            # Set the commands
            job_queue.run_once(self.set_commands, when=1)
            # Every day we check for a new version
            job_queue.run_repeating(self.check_version, interval=86400, first=1)
            # Every second we check for new posts to send to telegram - REPEATING NOT ONCE!
            job_queue.run_repeating(self.check_telegram_queue, interval=1, first=1)

            self.app.run_polling()
        except Exception as e:
            logger.error(f"Error initializing bot: {str(e)}", exc_info=True)

    ### TELEGRAM MINI APP ###
    
    async def open_web_app(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Open Telegram Mini App with Web UI"""
        try:
            # Import inside the function to avoid circular imports
            from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
            
            # Create web app URL from Railway environment or fallback
            web_app_url = "https://vs5-production.up.railway.app/"
            
            # Create inline keyboard with Web App button
            keyboard = [[InlineKeyboardButton("🌐 Open Web Interface", web_app=WebAppInfo(url=web_app_url))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🎉 <b>Vinted Notifications Web Interface</b>\n\n"
                "📊 Manage your queries, view items, and configure settings directly in Telegram!\n\n"
                "✨ <b>Features:</b>\n"
                "• 🔍 Add/remove search queries\n"
                "• 🧵 Set thread IDs for topics\n" 
                "• 📦 View found items\n"
                "• ⚙️ Configure bot settings\n"
                "• 📝 View logs\n\n"
                "👆 <b>Click the button below to open the web interface:</b>",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            logger.info("Web app message sent successfully")
        except ImportError as ie:
            logger.error(f"Import error in open_web_app: {str(ie)}", exc_info=True)
            try:
                await update.message.reply_text(
                    '🌐 <b>Web Interface</b>\n\n'
                    'Access the bot management interface at:\n'
                    'https://vs5-production.up.railway.app/\n\n'
                    '📱 <i>This link works on any device with a web browser.</i>',
                    parse_mode="HTML"
                )
            except Exception as fallback_error:
                logger.error(f"Fallback message also failed: {str(fallback_error)}", exc_info=True)
        except Exception as e:
            logger.error(f"Error opening web app: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    '🌐 <b>Web Interface</b>\n\n'
                    'Access the bot management interface at:\n'
                    'https://vs5-production.up.railway.app/\n\n'
                    '📱 <i>This link works on any device with a web browser.</i>',
                    parse_mode="HTML"
                )
            except Exception as fallback_error:
                logger.error(f"Fallback message also failed: {str(fallback_error)}", exc_info=True)

    ### QUERIES ###

    # Add a query to the db
    async def add_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            query = context.args
            if not query:
                await update.message.reply_text('No query provided.')
                return

            # Split the message into name=query if it contains an equal sign before the url. Store them separately
            if '=http' in query[0]:
                name, url = query[0].split('=', 1)
            else:
                name = None
                url = query[0]
            # Process the query using the core function
            message, is_new_query = core.process_query(url, name)

            if is_new_query:
                # Create a string with all the keywords
                query_list = core.get_formatted_query_list()
                await update.message.reply_text(f'{message} \nCurrent queries: \n{query_list}')
            else:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error adding query: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text('An error occurred while adding the query. Please try again later.')
            except:
                pass

    # Remove a query from the db
    async def remove_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            number = context.args
            if not number:
                await update.message.reply_text('No number provided.')
                return

            # Process the removal using the core function
            message, success = core.process_remove_query(number[0])

            if success:
                if number[0] == "all":
                    await update.message.reply_text(message)
                else:
                    # Get the updated list of queries
                    query_list = core.get_formatted_query_list()
                    await update.message.reply_text(f'{message} \nCurrent queries: \n{query_list}')
            else:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error removing query: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text('An error occurred while removing the query. Please try again later.')
            except:
                pass

    # get all queries from the db
    async def queries(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            query_list = core.get_formatted_query_list()
            await update.message.reply_text(f'Current queries: \n{query_list}')
        except Exception as e:
            logger.error(f"Error retrieving queries: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    'An error occurred while retrieving the queries. Please try again later.')
            except:
                pass

    ### ALLOWLIST ###

    async def clear_allowlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            db.clear_allowlist()
            await update.message.reply_text(f'Allowlist cleared. All countries are allowed.')
        except Exception as e:
            logger.error(f"Error clearing allowlist: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    'An error occurred while clearing the allowlist. Please try again later.')
            except:
                pass

    async def add_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            country = context.args
            if not country:
                await update.message.reply_text('No country provided')
                return

            # Process the country using the core function
            message, country_list = core.process_add_country(' '.join(country))

            await update.message.reply_text(f'{message} Current allowlist: {country_list}')
        except Exception as e:
            logger.error(f"Error adding country to allowlist: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    'An error occurred while adding the country to the allowlist. Please try again later.')
            except:
                pass

    async def remove_country(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            country = context.args
            if not country:
                await update.message.reply_text('No country provided')
                return

            # Process the country using the core function
            message, country_list = core.process_remove_country(' '.join(country))

            await update.message.reply_text(f'{message} Current allowlist: {country_list}')
        except Exception as e:
            logger.error(f"Error removing country from allowlist: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    'An error occurred while removing the country from the allowlist. Please try again later.')
            except:
                pass

    async def allowlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if db.get_allowlist() == 0:
                await update.message.reply_text(f'No allowlist set. All countries are allowed.')
            else:
                await update.message.reply_text(f'Current allowlist: {db.get_allowlist()}')
        except Exception as e:
            logger.error(f"Error retrieving allowlist: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    'An error occurred while retrieving the allowlist. Please try again later.')
            except:
                pass

    ### THREAD ID ###

    async def get_thread_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get the thread_id of the current forum topic/message thread"""
        try:
            message = update.message
            
            # Check if the message has a thread_id
            if hasattr(message, 'message_thread_id') and message.message_thread_id:
                thread_id = message.message_thread_id
                
                # Check if it's a forum topic
                if hasattr(message, 'is_topic_message') and message.is_topic_message:
                    await message.reply_text(
                        f"🧵 <b>Thread ID (Forum Topic):</b> <code>{thread_id}</code>\n\n"
                        f"📍 <i>This message is part of a forum topic.</i>\n"
                        f"💡 <i>Use this ID to send messages to this specific topic.</i>",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        f"🧵 <b>Thread ID:</b> <code>{thread_id}</code>\n\n"
                        f"📍 <i>This message is part of a thread.</i>\n"
                        f"💡 <i>Use this ID to send messages to this specific thread.</i>",
                        parse_mode="HTML"
                    )
            else:
                # Check if it's a regular group/supergroup message
                chat_type = message.chat.type
                if chat_type in ['group', 'supergroup']:
                    await message.reply_text(
                        f"ℹ️ <b>No Thread ID</b>\n\n"
                        f"📍 <i>This message is in the main chat (not in a forum topic or message thread).</i>\n"
                        f"💡 <i>Chat type: {chat_type}</i>",
                        parse_mode="HTML"
                    )
                elif chat_type == 'private':
                    await message.reply_text(
                        f"ℹ️ <b>Private Chat</b>\n\n"
                        f"📍 <i>Thread IDs are only available in groups, supergroups, and forum topics.</i>",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        f"ℹ️ <b>No Thread ID</b>\n\n"
                        f"📍 <i>Chat type: {chat_type}</i>\n"
                        f"💡 <i>Thread IDs are available in forum topics and message threads.</i>",
                        parse_mode="HTML"
                    )
                    
        except Exception as e:
            logger.error(f"Error getting thread ID: {str(e)}", exc_info=True)
            try:
                await update.message.reply_text(
                    f"❌ <b>Error</b>\n\n"
                    f"<i>An error occurred while getting thread ID. Please try again later.</i>",
                    parse_mode="HTML"
                )
            except:
                pass

    ### TELEGRAM SPECIFIC FUNCTIONS ###

    async def send_new_post(self, content, url, text, buy_url=None, buy_text=None, thread_id=None, photo_url=None):
        try:
            async with self.bot:
                chat_ID = str(db.get_parameter("telegram_chat_id"))
                buttons = [[InlineKeyboardButton(text=text, url=url)]]
                if buy_url and buy_text:
                    buttons.append([InlineKeyboardButton(text=buy_text, url=buy_url)])
                
                # Try to send to specific thread if thread_id is provided
                try:
                    if photo_url:
                        # Send as photo with caption
                        if thread_id:
                            await self.bot.send_photo(
                                chat_ID,
                                photo=photo_url,
                                caption=content,
                                parse_mode="HTML",
                                read_timeout=40,
                                write_timeout=40,
                                reply_markup=InlineKeyboardMarkup(buttons),
                                message_thread_id=thread_id
                            )
                        else:
                            await self.bot.send_photo(
                                chat_ID,
                                photo=photo_url,
                                caption=content,
                                parse_mode="HTML",
                                read_timeout=40,
                                write_timeout=40,
                                reply_markup=InlineKeyboardMarkup(buttons)
                            )
                    else:
                        # Send as text message if no photo
                        if thread_id:
                            await self.bot.send_message(
                                chat_ID, 
                                content, 
                                parse_mode="HTML",
                                read_timeout=40,
                                write_timeout=40,
                                reply_markup=InlineKeyboardMarkup(buttons),
                                message_thread_id=thread_id
                            )
                        else:
                            # Send to main chat if no thread_id
                            await self.bot.send_message(
                                chat_ID, 
                                content, 
                                parse_mode="HTML",
                                read_timeout=40,
                                write_timeout=40,
                                reply_markup=InlineKeyboardMarkup(buttons)
                            )
                except Exception as thread_error:
                    # If sending to thread fails, fallback to main chat
                    logger.warning(f"Failed to send to thread {thread_id}: {thread_error}. Sending to main chat.")
                    if photo_url:
                        await self.bot.send_photo(
                            chat_ID,
                            photo=photo_url,
                            caption=content,
                            parse_mode="HTML",
                            read_timeout=40,
                            write_timeout=40,
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                    else:
                        await self.bot.send_message(
                            chat_ID, 
                            content, 
                            parse_mode="HTML",
                            read_timeout=40,
                            write_timeout=40,
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                    
        except RetryAfter as e:
            retry_after = e.retry_after
            logger.error(f"Flood control exceeded. Retrying in {retry_after + 2} seconds")
            await asyncio.sleep(retry_after + 2)
            # Retry sending the message
            await self.send_new_post(content, url, text, buy_url, buy_text, thread_id, photo_url)
        except Exception as e:
            logger.error(f"Error sending new post: {str(e)}", exc_info=True)

    async def check_version(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            # get latest version from the repository
            should_update, VER, latest_version, url = core.check_version()

            if not should_update:
                await self.send_new_post(f"Version {latest_version} is now available. Please update the bot.", url,
                                         "Open Github")
        except Exception as e:
            logger.error(f"Error checking for new version: {str(e)}", exc_info=True)

    async def check_telegram_queue(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Process all items in queue (no infinite loop since it's called every second)
            processed = 0
            while not self.new_items_queue.empty() and processed < 20:  # Increased limit to 20 items per call
                queue_item = self.new_items_queue.get()
                logger.info(f"[TELEGRAM] Processing queue item: {queue_item}")
                
                # Handle different queue formats: (content, url, text, buy_url, buy_text, thread_id, photo_url)
                if len(queue_item) == 7:
                    content, url, text, buy_url, buy_text, thread_id, photo_url = queue_item
                elif len(queue_item) == 6:
                    content, url, text, buy_url, buy_text, thread_id = queue_item
                    photo_url = None
                else:
                    content, url, text, buy_url, buy_text = queue_item
                    thread_id = None
                    photo_url = None
                
                logger.info(f"[TELEGRAM] Sending to Telegram: {content[:50]}...")
                await self.send_new_post(content, url, text, buy_url, buy_text, thread_id, photo_url)
                logger.info(f"[TELEGRAM] Item sent successfully!")
                processed += 1
                
            if processed > 0:
                logger.info(f"[TELEGRAM] Processed {processed} items from queue")
        except Exception as e:
            logger.error(f"Error checking telegram queue: {str(e)}", exc_info=True)

    async def set_commands(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.bot.set_my_commands([
                ("hello", "Verify if bot is running"),
                ("app", "Open Web Interface (Mini App)"),
                ("add_query", "Add a keyword to the bot"),
                ("remove_query", "Remove a keyword from the bot"),
                ("queries", "List all keywords"),
                ("clear_allowlist", "Clear the allowlist"),
                ("add_country", "Add a country to the allowlist"),
                ("remove_country", "Remove a country from the allowlist"),
                ("allowlist", "List all countries in the allowlist"),
                ("thread_id", "Get thread ID of current forum topic")
            ])
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Error setting bot commands: {str(e)}", exc_info=True)
