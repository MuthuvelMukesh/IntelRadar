import logging
from telegram.ext import ApplicationBuilder, CommandHandler
from .config import TG_BOT_TOKEN
from .db import init_db
from .bot import start, update_feed, get_today, get_category

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # 1. Initialize DB
    init_db()
    
    # 2. Build Bot Application
    application = ApplicationBuilder().token(TG_BOT_TOKEN).build()
    
    # 3. Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("update", update_feed))
    application.add_handler(CommandHandler("today", get_today))
    application.add_handler(CommandHandler("category", get_category))
    
    # 4. Run
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
