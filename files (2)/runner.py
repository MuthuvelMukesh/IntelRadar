import logging
from datetime import time as dt_time

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    JobQueue,
)

from .config import TG_BOT_TOKEN, DIGEST_HOUR, FETCH_INTERVAL_MINUTES
from .db import init_db
from .bot import (
    start,
    update_feed,
    get_today,
    get_digest,
    get_category,
    subscribe,
    subscribe_callback,
    my_prefs,
    add_channel,
    remove_channel,
    list_channels,
)
from .scheduler import scheduled_fetch, send_morning_digest

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not TG_BOT_TOKEN:
        raise RuntimeError("TG_BOT_TOKEN is not set in .env")

    # 1. Init database
    init_db()
    logger.info("Database initialized.")

    # 2. Build app
    application = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    # 3. Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", get_today))
    application.add_handler(CommandHandler("digest", get_digest))
    application.add_handler(CommandHandler("category", get_category))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("myprefs", my_prefs))
    application.add_handler(CommandHandler("update", update_feed))
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("channels", list_channels))

    # 4. Inline keyboard callback
    application.add_handler(CallbackQueryHandler(subscribe_callback, pattern="^sub_"))

    # 5. Scheduled jobs
    job_queue: JobQueue = application.job_queue

    # Periodic fetch every N minutes
    job_queue.run_repeating(
        scheduled_fetch,
        interval=FETCH_INTERVAL_MINUTES * 60,
        first=30,  # first run 30s after startup
        name="periodic_fetch",
    )

    # Morning digest at 6:00 AM UTC daily
    job_queue.run_daily(
        send_morning_digest,
        time=dt_time(hour=DIGEST_HOUR, minute=0, second=0),
        name="morning_digest",
    )

    logger.info(f"Bot started. Digest at {DIGEST_HOUR:02d}:00 UTC. Fetch every {FETCH_INTERVAL_MINUTES}min.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
