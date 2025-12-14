from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from .db import SessionLocal
from .models import NewsItem
from .fetcher import NewsFetcher
from .config import LOOKBACK_HOURS, VALID_CATEGORIES

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "Welcome to Antigravity Bot!\n\n"
        "Commands:\n"
        "/update - Fetch new messages (may take time)\n"
        "/today - Show summarized news from the last 24h\n"
        f"/category <name> - Filter by category ({', '.join(VALID_CATEGORIES)})"
    )

async def update_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers the fetcher manually."""
    await update.message.reply_text("Fetching new items from channels... please wait.")
    
    # Run fetcher
    # NOTE: In a production app, do this in a separate thread/task so it doesn't block
    fetcher = NewsFetcher()
    try:
        count = await fetcher.fetch_recent_messages()
        await fetcher.close()
        await update.message.reply_text(f"Done! Fetched {count} new items.")
    except Exception as e:
        logger.error(f"Error fetching: {e}")
        await update.message.reply_text(f"Error fetching items: {e}")

def format_item(item: NewsItem):
    """Helper to format a news item string."""
    return (
        f"<b>[{item.category.upper()}]</b> {item.source}/{item.channel}\n"
        f"<i>{item.summary or 'No summary'}</i>\n"
        f"Tags: {item.tags}\n"
        f"<a href='{item.link}'>Link</a>\n\n"
    )

async def get_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows items from the last 24h (or configured lookback)."""
    cutoff = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    
    with SessionLocal() as db:
        items = db.query(NewsItem).filter(NewsItem.date >= cutoff).order_by(NewsItem.date.desc()).all()
        
        if not items:
            await update.message.reply_text("No news found in the last 24h.")
            return

        msg = f"<b>News from last {LOOKBACK_HOURS}h:</b>\n\n"
        for item in items:
            # Telegram has message length limits (4096 chars). 
            # Simple chunking for safety:
            if len(msg) + len(format_item(item)) > 4000:
                await update.message.reply_html(msg)
                msg = ""
            msg += format_item(item)
            
        if msg:
            await update.message.reply_html(msg)

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filter by category."""
    if not context.args:
        await update.message.reply_text(f"Usage: /category <name>\nValid: {', '.join(VALID_CATEGORIES)}")
        return
        
    cat = context.args[0].lower()
    
    with SessionLocal() as db:
        items = db.query(NewsItem).filter(NewsItem.category == cat).order_by(NewsItem.date.desc()).limit(20).all()
        
        if not items:
            await update.message.reply_text(f"No recent items found for category: {cat}")
            return

        msg = f"<b>Latest in {cat}:</b>\n\n"
        for item in items:
            if len(msg) + len(format_item(item)) > 4000:
                await update.message.reply_html(msg)
                msg = ""
            msg += format_item(item)
            
        if msg:
            await update.message.reply_html(msg)
