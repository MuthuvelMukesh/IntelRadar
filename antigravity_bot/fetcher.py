import asyncio
import json
import logging
from datetime import datetime, timedelta

from telethon import TelegramClient

from .config import TG_API_ID, TG_API_HASH, MESSAGES_PER_CHANNEL, LOOKBACK_HOURS
from .db import SessionLocal
from .models import NewsItem, MonitoredChannel
from .llm import LLMClient

logger = logging.getLogger(__name__)

# Telethon session file name
SESSION_NAME = "antigravity_session"


class NewsFetcher:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, TG_API_ID, TG_API_HASH)
        self.llm = LLMClient()

    async def get_active_channels(self) -> list[str]:
        """Load active channel list from the database."""
        with SessionLocal() as db:
            channels = db.query(MonitoredChannel).filter(MonitoredChannel.active == True).all()
            return [c.username for c in channels]

    async def fetch_recent_messages(self) -> int:
        """
        Fetches recent messages from all active channels, classifies them, and stores new ones.
        Returns count of new items added.
        """
        logger.info("Starting fetch cycle...")

        channels = await self.get_active_channels()
        if not channels:
            logger.warning("No active channels configured.")
            return 0

        try:
            await self.client.start()
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            return 0

        cutoff = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
        new_count = 0

        for channel in channels:
            logger.info(f"Fetching from @{channel}...")
            try:
                entity = await self.client.get_entity(channel)
                messages_to_process = []

                async for message in self.client.iter_messages(
                    entity, limit=MESSAGES_PER_CHANNEL
                ):
                    if not message.text:
                        continue
                    if message.date and message.date.replace(tzinfo=None) < cutoff:
                        break

                    msg_link = f"https://t.me/{channel}/{message.id}"

                    with SessionLocal() as db:
                        exists = (
                            db.query(NewsItem)
                            .filter(NewsItem.link == msg_link)
                            .first()
                        )
                    if exists:
                        continue

                    messages_to_process.append((message, msg_link))

                # Process in batches to avoid rate limits
                for message, msg_link in messages_to_process:
                    logger.info(f"  Processing message {message.id} from @{channel}")
                    analysis = self.llm.classify_and_summarize(message.text)

                    item = NewsItem(
                        source="telegram",
                        channel=channel,
                        text=message.text,
                        date=message.date.replace(tzinfo=None)
                        if message.date
                        else datetime.utcnow(),
                        link=msg_link,
                        category=analysis["category"],
                        region=analysis.get("region"),
                        tags=json.dumps(analysis.get("tags", [])),
                        summary=analysis["summary"],
                        importance=analysis["importance"],
                    )

                    with SessionLocal() as db:
                        db.add(item)
                        db.commit()
                        new_count += 1

                    # Small sleep to be polite to OpenRouter free tier
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing @{channel}: {e}")
                continue

        logger.info(f"Fetch completed. {new_count} new items saved.")
        return new_count

    async def close(self):
        if self.client.is_connected():
            await self.client.disconnect()
