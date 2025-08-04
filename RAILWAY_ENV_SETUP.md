# Railway Environment Variables Setup

This document explains how to configure environment variables for the Vinted Notifications bot when deploying to Railway.

## Required Environment Variables

### Database Configuration
- `DATABASE_URL` - PostgreSQL database connection string (automatically provided by Railway PostgreSQL service)

### Telegram Bot Configuration  
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (get from @BotFather)
- `TELEGRAM_CHAT_ID` - Your Telegram chat/group ID where notifications will be sent

## How to Set Environment Variables in Railway

1. **In Railway Dashboard:**
   - Go to your project
   - Click on the "Variables" tab
   - Add each variable with its corresponding value

2. **Required Variables:**
   ```
   TELEGRAM_BOT_TOKEN=8028751125:AAEky-PBAuaf5J8_8LcZPRnbR7qZEr1ocw4
   TELEGRAM_CHAT_ID=-1002707972747
   ```

3. **PostgreSQL Database:**
   - Add a PostgreSQL service to your Railway project
   - Railway will automatically provide the `DATABASE_URL` variable

## Optional Environment Variables

### Web UI Configuration
- `WEB_UI_PORT` - Port for the web interface (default: 8000)

### Proxy Configuration (if needed)
- `PROXY_LIST` - List of proxies separated by semicolons
- `PROXY_LIST_LINK` - URL to fetch proxies from

## Important Notes

1. **Security**: Never commit sensitive tokens to your repository. Always use environment variables for sensitive data.

2. **Database Migration**: When you first deploy, the bot will automatically:
   - Create the database schema
   - Run any pending migrations
   - Set up initial configuration

3. **Supergroup with Topics**: 
   - Make sure your Telegram chat is a supergroup with topics enabled
   - Each query can be assigned a specific thread_id to send messages to different topics
   - If no thread_id is specified or if sending to a topic fails, messages will be sent to the main chat

4. **Thread ID Configuration**:
   - You can set thread_id for each query through the web interface
   - Go to the Queries page and edit the Thread ID field for each query
   - Leave empty for main chat, or enter the topic's message thread ID

## Getting Your Chat/Group ID

1. Add your bot to the desired chat/group
2. Send a message in the chat
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for the `chat` object and copy the `id` value (it will be negative for groups)

## Getting Thread IDs for Topics

1. Enable topics in your supergroup
2. Create topics as needed
3. Forward a message from each topic to @userinfobot
4. The bot will show you the `message_thread_id` which you can use in the web interface

## Deployment Steps

1. Fork/clone this repository
2. Connect it to Railway
3. Add a PostgreSQL service
4. Set the environment variables listed above
5. Deploy the application
6. Access the web interface at your Railway app URL
7. Configure your queries and thread IDs through the web interface