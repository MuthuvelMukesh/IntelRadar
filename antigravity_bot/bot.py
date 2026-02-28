import json
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

from .db import SessionLocal
from .models import NewsItem, MonitoredChannel, UserSubscription
from .config import (
    VALID_CATEGORIES, CATEGORY_LABELS, VALID_REGIONS,
    LOOKBACK_HOURS, ADMIN_USER_IDS
)
from .llm import LLMClient

logger = logging.getLogger(__name__)
llm = LLMClient()


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def get_or_create_subscription(db, user_id: int, chat_id: int) -> UserSubscription:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub:
        sub = UserSubscription(user_id=user_id, chat_id=chat_id)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def format_item(item: NewsItem) -> str:
    label = CATEGORY_LABELS.get(item.category, item.category)
    tags = []
    try:
        tags = json.loads(item.tags) if item.tags else []
    except Exception:
        pass
    tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
    stars = "⭐" * min(item.importance // 3, 3) if item.importance else ""

    return (
        f"{stars} <b>{label}</b> | <code>@{item.channel}</code>\n"
        f"<i>{item.summary or 'No summary'}</i>\n"
        f"{tag_str}\n"
        f"<a href='{item.link}'>🔗 Source</a> · "
        f"{item.date.strftime('%d %b %H:%M') if item.date else ''}\n\n"
    )


async def send_chunked(update_or_message, text: str, parse_mode=ParseMode.HTML):
    """Send long text in safe chunks ≤ 4096 chars."""
    target = update_or_message
    for i in range(0, len(text), 4000):
        chunk = text[i : i + 4000]
        await target.reply_html(chunk) if hasattr(target, "reply_html") else await target.reply_text(chunk)


# ─────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with SessionLocal() as db:
        get_or_create_subscription(db, user.id, update.effective_chat.id)

    cats = "\n".join(f"  <code>{k}</code> — {v}" for k, v in CATEGORY_LABELS.items())
    text = (
        f"👋 <b>Welcome to Antigravity News Bot</b>, {user.first_name}!\n\n"
        "I fetch news from Telegram channels, classify it with AI, and deliver "
        "smart summaries — filtered by your interests.\n\n"
        "<b>📋 Commands</b>\n"
        "/today — Last 24h news digest\n"
        "/digest [category] — AI-written digest for a category\n"
        "/category [name] — Latest items in a category\n"
        "/subscribe — Set your category/region preferences\n"
        "/myprefs — Show your current preferences\n"
        "/update — Force-fetch new messages (admin)\n"
        "/addchannel @username — Add a channel (admin)\n"
        "/removechannel @username — Remove a channel (admin)\n"
        "/channels — List monitored channels\n\n"
        f"<b>📂 Categories</b>\n{cats}\n\n"
        "Your morning digest will arrive at 6:00 AM daily 🌅"
    )
    await update.message.reply_html(text)


# ─────────────────────────────────────────────
#  /today — raw items from last 24h
# ─────────────────────────────────────────────

async def get_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cutoff = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)

    with SessionLocal() as db:
        sub = get_or_create_subscription(db, user.id, update.effective_chat.id)
        query = db.query(NewsItem).filter(NewsItem.date >= cutoff)

        # Apply user category filter
        cats = sub.get_categories()
        if cats != "all":
            query = query.filter(NewsItem.category.in_(cats))

        items = query.order_by(NewsItem.date.desc()).limit(50).all()

        if not items:
            filter_note = f" in your subscribed categories ({', '.join(cats)})" if cats != "all" else ""
            await update.message.reply_text(f"No news found in the last {LOOKBACK_HOURS}h{filter_note}.")
            return

        msg = f"<b>📰 News — last {LOOKBACK_HOURS}h</b> ({len(items)} items)\n\n"
        for item in items:
            chunk = format_item(item)
            if len(msg) + len(chunk) > 4000:
                await update.message.reply_html(msg)
                msg = ""
            msg += chunk
        if msg:
            await update.message.reply_html(msg)


# ─────────────────────────────────────────────
#  /digest [category] — AI-written digest
# ─────────────────────────────────────────────

async def get_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat = context.args[0].lower() if context.args else None

    if cat and cat not in VALID_CATEGORIES:
        cats_list = ", ".join(sorted(VALID_CATEGORIES))
        await update.message.reply_text(f"Unknown category. Valid: {cats_list}")
        return

    cutoff = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)

    with SessionLocal() as db:
        query = db.query(NewsItem).filter(NewsItem.date >= cutoff)
        if cat:
            query = query.filter(NewsItem.category == cat)
        items = query.order_by(NewsItem.importance.desc(), NewsItem.date.desc()).limit(40).all()

    if not items:
        await update.message.reply_text("No items found for digest.")
        return

    label = CATEGORY_LABELS.get(cat, "All Categories") if cat else "All Categories"
    await update.message.reply_text(f"⏳ Generating digest for {label}...")

    items_data = [
        {"category": i.category, "summary": i.summary, "channel": i.channel,
         "date": i.date.strftime("%d %b") if i.date else ""}
        for i in items
    ]
    digest_text = llm.generate_digest(items_data, cat)

    header = f"<b>🗞 Morning Digest — {label}</b>\n<i>{datetime.utcnow().strftime('%d %B %Y')}</i>\n\n"
    await update.message.reply_html(header + digest_text)


# ─────────────────────────────────────────────
#  /category [name] — latest items in category
# ─────────────────────────────────────────────

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        cats_list = "\n".join(f"  <code>{k}</code> — {v}" for k, v in CATEGORY_LABELS.items())
        await update.message.reply_html(f"Usage: /category [name]\n\n{cats_list}")
        return

    cat = context.args[0].lower()
    if cat not in VALID_CATEGORIES:
        await update.message.reply_text(f"Unknown category '{cat}'. Use /category to list them.")
        return

    with SessionLocal() as db:
        items = (
            db.query(NewsItem)
            .filter(NewsItem.category == cat)
            .order_by(NewsItem.importance.desc(), NewsItem.date.desc())
            .limit(20)
            .all()
        )

    if not items:
        await update.message.reply_text(f"No recent items in category: {cat}")
        return

    label = CATEGORY_LABELS.get(cat, cat)
    msg = f"<b>{label}</b> — latest items\n\n"
    for item in items:
        chunk = format_item(item)
        if len(msg) + len(chunk) > 4000:
            await update.message.reply_html(msg)
            msg = ""
        msg += chunk
    if msg:
        await update.message.reply_html(msg)


# ─────────────────────────────────────────────
#  /subscribe — inline keyboard to pick preferences
# ─────────────────────────────────────────────

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for i, (key, label) in enumerate(CATEGORY_LABELS.items()):
        row.append(InlineKeyboardButton(label, callback_data=f"sub_cat:{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton("✅ Subscribe ALL", callback_data="sub_cat:all"),
        InlineKeyboardButton("📋 Done", callback_data="sub_done"),
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select categories to subscribe to (tap to toggle, then Done):",
        reply_markup=reply_markup,
    )


async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    with SessionLocal() as db:
        sub = get_or_create_subscription(db, user_id, query.message.chat_id)

        if data == "sub_done":
            cats = sub.get_categories()
            label = "all categories" if cats == "all" else ", ".join(cats)
            await query.edit_message_text(f"✅ Subscribed to: {label}")
            return

        if data == "sub_cat:all":
            sub.categories = "all"
            db.commit()
            await query.edit_message_text("✅ Subscribed to ALL categories. Use /myprefs to review.")
            return

        cat = data.replace("sub_cat:", "")
        current = sub.get_categories()
        if current == "all":
            current = list(VALID_CATEGORIES)

        if cat in current:
            current.remove(cat)
        else:
            current.append(cat)

        sub.categories = ",".join(current) if current else "other"
        db.commit()
        await query.answer(f"Toggled: {cat}")


# ─────────────────────────────────────────────
#  /myprefs
# ─────────────────────────────────────────────

async def my_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with SessionLocal() as db:
        sub = get_or_create_subscription(db, user_id, update.effective_chat.id)
        cats = sub.get_categories()
        cat_str = "All categories" if cats == "all" else ", ".join(cats)

    await update.message.reply_html(
        f"<b>Your preferences</b>\n\n"
        f"📂 Categories: <code>{cat_str}</code>\n"
        f"🌅 Morning digest: {'✅ ON' if sub.digest_on else '❌ OFF'}\n"
        f"🔔 Alerts: {'✅ ON' if sub.alerts_on else '❌ OFF'}\n\n"
        "Use /subscribe to change categories."
    )


# ─────────────────────────────────────────────
#  /update — manual fetch (admin)
# ─────────────────────────────────────────────

async def update_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only.")
        return

    from .fetcher import NewsFetcher
    await update.message.reply_text("⏳ Fetching new items from channels...")
    fetcher = NewsFetcher()
    try:
        count = await fetcher.fetch_recent_messages()
        await fetcher.close()
        await update.message.reply_text(f"✅ Done! Fetched {count} new items.")
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────
#  /addchannel & /removechannel (admin)
# ─────────────────────────────────────────────

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addchannel @channelname")
        return

    username = context.args[0].lstrip("@").lower()

    with SessionLocal() as db:
        existing = db.query(MonitoredChannel).filter(MonitoredChannel.username == username).first()
        if existing:
            if not existing.active:
                existing.active = True
                db.commit()
                await update.message.reply_text(f"✅ Re-activated @{username}")
            else:
                await update.message.reply_text(f"ℹ️ @{username} is already monitored.")
            return

        channel = MonitoredChannel(username=username, added_by=user_id)
        db.add(channel)
        db.commit()

    await update.message.reply_text(
        f"✅ Added @{username} to monitored channels.\n"
        "It will be fetched on the next update cycle."
    )


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removechannel @channelname")
        return

    username = context.args[0].lstrip("@").lower()

    with SessionLocal() as db:
        channel = db.query(MonitoredChannel).filter(MonitoredChannel.username == username).first()
        if not channel:
            await update.message.reply_text(f"@{username} is not in the list.")
            return
        channel.active = False
        db.commit()

    await update.message.reply_text(f"🗑 Removed @{username} from monitoring.")


# ─────────────────────────────────────────────
#  /channels — list monitored channels
# ─────────────────────────────────────────────

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as db:
        channels = db.query(MonitoredChannel).filter(MonitoredChannel.active == True).all()

    if not channels:
        await update.message.reply_text(
            "No channels monitored yet.\nAdmins can use /addchannel @username to add one."
        )
        return

    lines = "\n".join(f"• @{c.username}" for c in channels)
    await update.message.reply_html(f"<b>📡 Monitored Channels ({len(channels)})</b>\n\n{lines}")
