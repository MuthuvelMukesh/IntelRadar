import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from .config import TG_API_ID, TG_API_HASH, CHANNEL_USERNAMES
from .models import NewsItem
from .db import SessionLocal
from .llm import LLMClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsFetcher:
    def __init__(self):
        self.client = TelegramClient('anon', TG_API_ID, TG_API_HASH)
        self.llm = LLMClient()

    async def fetch_recent_messages(self, limit=20):
        """
        Fetches recent messages from configured channels and stores new ones.
        """
        logger.info("Starting fetch cycle...")
        try:
            await self.client.start()
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            return 0
        
        new_items_count = 0
        
        with SessionLocal() as db:
            for channel in CHANNEL_USERNAMES:
                logger.info(f"Fetching from {channel}...")
                try:
                    # Get entity to ensure we can access it
                    entity = await self.client.get_entity(channel)
                    
                    async for message in self.client.iter_messages(entity, limit=limit):
                        if not message.text:
                            continue
                            
                        # Construct a unique link/ID
                        msg_link = f"https://t.me/{channel}/{message.id}"
                        
                        # Check deduplication
                        exists = db.query(NewsItem).filter(NewsItem.link == msg_link).first()
                        if exists:
                            continue
                            
                        # Process with LLM
                        logger.info(f"Processing new message from {channel}")
                        analysis = self.llm.classify_and_summarize(message.text)
                        
                        # Create NewsItem
                        item = NewsItem(
                            source="telegram",
                            channel=channel,
                            text=message.text,
                            date=message.date.replace(tzinfo=None) if message.date else datetime.utcnow(),
                            link=msg_link,
                            category=analysis.get("category"),
                            tags=analysis.get("tags"),
                            summary=analysis.get("summary")
                        )
                        
                        db.add(item)
                        new_items_count += 1
            
            db.commit()
            
        logger.info(f"Fetch completed. {new_items_count} new items.")
        return new_items_count

    async def close(self):
        await self.client.disconnect()
