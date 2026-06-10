from telethon import TelegramClient
from app.config.settings import env_settings
import asyncio
import os

# Create a session file in the root directory
# We specify the full path to avoid issues with different working directories
SESSION_PATH = os.path.join(os.path.dirname(__file__), "../../", env_settings.TELEGRAM_SESSION_NAME)

async def send_telegram_message(message: str):
    """
    Sends a message to your own Telegram account.
    This is an async function.
    """
    client = TelegramClient(
        SESSION_PATH, 
        env_settings.TELEGRAM_API_ID, 
        env_settings.TELEGRAM_API_HASH
    )
    
    # Connect and ensure started (might require manual code entry the first time)
    await client.start(phone=env_settings.TELEGRAM_PHONE_NUMBER)
    
    async with client:
        await client.send_message(env_settings.TELEGRAM_RECEIPT_EMAIL, f"📢 **Sync System Log Notification**\n\n{message}")

def send_telegram_log(message: str):
    """
    Synchronous wrapper for sending a telegram message.
    Can be used in standard functions.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # If we are already in an event loop (e.g. FastAPI/Uvicorn)
        # using create_task is better
        loop.create_task(send_telegram_message(message))
    else:
        loop.run_until_complete(send_telegram_message(message))
