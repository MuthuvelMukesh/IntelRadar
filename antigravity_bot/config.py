import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Config
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

# Source Config
# Parse comma-separated string into a list, strip whitespace
CHANNEL_USERNAMES = [
    u.strip() for u in os.getenv("CHANNEL_USERNAMES", "").split(",") if u.strip()
]

# LLM Config
LLM_API_KEY = os.getenv("GEMINI_API_KEY")

# Application Config
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))

# Categories validation list
VALID_CATEGORIES = {
    "trading", "markets", "crypto", "geopolitics", "macro",
    "finance", "inflation", "equities", "oil", "bonds", "other"
}
