import logging
from datetime import datetime, timedelta, time as dt_time

from telegram.ext import ContextTypes

from .config import DIGEST_HOUR, FETCH_INTERVAL_MINUTES, LOOKBACK_HOURS, CATEGORY_LABELS
from .db import SessionLocal
from .models import NewsItem, UserSubscription
from .llm import LLMClient

logger = logging.getLogger(__name__)
llm = LLMClient()


async def scheduled_fetch(context: ContextTypes.DEFAULT_TYPE):
    """Runs every FETCH_INTERVAL_MINUTES to pull new messages."""
    logger.info("Scheduled fetch triggered.")
    from .fetcher import NewsFetcher
    fetcher = NewsFetcher()
    try:
        count = await fetcher.fetch_recent_messages()
        logger.info(f"Scheduled fetch: {count} new items.")
    except Exception as e:
        logger.error(f"Scheduled fetch error: {e}")
    finally:
        await fetcher.close()


async def send_morning_digest(context: ContextTypes.DEFAULT_TYPE):
    """
    Sends each subscribed user a personalized morning digest
    based on their category preferences.
    """
    logger.info("Sending morning digests...")
    cutoff = datetime.utcnow() - timedelta(hours=24)

    with SessionLocal() as db:
        subscribers = db.query(UserSubscription).filter(
            UserSubscription.digest_on == True
        ).all()

        if not subscribers:
            logger.info("No digest subscribers.")
            return

        for sub in subscribers:
            try:
                cats = sub.get_categories()
                query = db.query(NewsItem).filter(NewsItem.date >= cutoff)
                if cats != "all":
                    query = query.filter(NewsItem.category.in_(cats))

                items = query.order_by(
                    NewsItem.importance.desc(), NewsItem.date.desc()
                ).limit(40).all()

                if not items:
                    await context.bot.send_message(
                        chat_id=sub.chat_id,
                        text="🌅 Good morning! No new items in your categories since yesterday.",
                    )
                    continue

                items_data = [
                    {
                        "category": i.category,
                        "summary": i.summary,
                        "channel": i.channel,
                        "date": i.date.strftime("%d %b") if i.date else "",
                    }
                    for i in items
                ]

                label = "your subscribed topics" if cats != "all" else "all categories"
                digest = llm.generate_digest(items_data)

                date_str = datetime.utcnow().strftime("%A, %d %B %Y")
                header = (
                    f"🌅 <b>Morning Digest — {date_str}</b>\n"
                    f"<i>Covering {label} · {len(items)} stories</i>\n\n"
                )

                # Send digest
                await context.bot.send_message(
                    chat_id=sub.chat_id,
                    text=header + digest,
                    parse_mode="HTML",
                )

                # Send top 5 items with links
                top_items = items[:5]
                links_msg = "<b>📎 Top Stories</b>\n\n"
                from .bot import format_item
                for item in top_items:
                    links_msg += format_item(item)

                await context.bot.send_message(
                    chat_id=sub.chat_id,
                    text=links_msg,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

            except Exception as e:
                logger.error(f"Error sending digest to user {sub.user_id}: {e}")
                continue

    logger.info("Morning digests sent.")


async def send_importance_alert(context: ContextTypes.DEFAULT_TYPE, item: NewsItem):
    """
    Sends high-importance (>=8) news alerts to users who opted in.
    Called by the fetcher when a high-importance item is saved.
    """
    with SessionLocal() as db:
        subscribers = db.query(UserSubscription).filter(
            UserSubscription.alerts_on == True
        ).all()

        for sub in subscribers:
            cats = sub.get_categories()
            if cats != "all" and item.category not in cats:
                continue
            try:
                label = CATEGORY_LABELS.get(item.category, item.category)
                msg = (
                    f"🚨 <b>BREAKING — {label}</b>\n\n"
                    f"<i>{item.summary}</i>\n\n"
                    f"<a href='{item.link}'>🔗 Source @{item.channel}</a>"
                )
                await context.bot.send_message(
                    chat_id=sub.chat_id,
                    text=msg,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Alert send error for user {sub.user_id}: {e}")
