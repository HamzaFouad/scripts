"""
Notification module for sending messages and files via Telegram bot.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    A class to handle Telegram notifications for bot operations.
    """
    
    def __init__(self, bot_token=None, chat_id=None):
        """
        Initialize the Telegram notifier.
        
        Args:
            bot_token (str, optional): Telegram bot token. If not provided, 
                                      will try to get from TELEGRAM_BOT_TOKEN env var.
            chat_id (str, optional): Telegram chat/channel ID. If not provided, 
                                    will try to get from TELEGRAM_CHAT_ID env var.
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("Telegram bot token is required. Set TELEGRAM_BOT_TOKEN in .env file.")
        if not self.chat_id:
            raise ValueError("Telegram chat/channel ID is required. Set TELEGRAM_CHAT_ID in .env file.")
        
        self.bot = Bot(token=self.bot_token)
    
    async def send_message(self, message):
        """
        Send a text message to the Telegram chat/channel.
        
        Args:
            message (str): The message to send.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info("Message sent successfully to Telegram")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return False
    
    async def send_document(self, file_path, caption=None):
        """
        Send a document (e.g., CSV file) to the Telegram chat/channel.
        
        Args:
            file_path (str): Path to the file to send.
            caption (str, optional): Caption for the document.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            with open(file_path, 'rb') as document:
                await self.bot.send_document(
                    chat_id=self.chat_id,
                    document=document,
                    filename=os.path.basename(file_path),
                    caption=caption
                )
            logger.info(f"Document sent successfully to Telegram: {file_path}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send document to Telegram: {e}")
            return False
    
    async def send_completion_notification(self, message, csv_file_path=None):
        """
        Send a completion notification with optional CSV file.
        
        Args:
            message (str): The completion message.
            csv_file_path (str, optional): Path to CSV file to attach.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        success = True
        
        # Send message
        if not await self.send_message(message):
            success = False
        
        # Send CSV file if provided
        if csv_file_path and os.path.exists(csv_file_path):
            caption = f"Summary CSV file: {os.path.basename(csv_file_path)}"
            if not await self.send_document(csv_file_path, caption=caption):
                success = False
        
        return success


def send_telegram_notification(message, csv_file_path=None, bot_token=None, chat_id=None):
    """
    Convenience function to send a Telegram notification synchronously.
    
    Args:
        message (str): The message to send.
        csv_file_path (str, optional): Path to CSV file to attach.
        bot_token (str, optional): Telegram bot token.
        chat_id (str, optional): Telegram chat/channel ID.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    import asyncio
    
    try:
        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If no event loop is running, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(
            notifier.send_completion_notification(message, csv_file_path)
        )
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False
