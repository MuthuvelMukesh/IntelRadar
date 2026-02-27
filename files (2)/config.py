import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

# --- OpenRouter LLM ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Best free model for summarization/classification tasks
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# --- App Settings ---
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "6"))   # 6 AM daily digest
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "30"))
MESSAGES_PER_CHANNEL = int(os.getenv("MESSAGES_PER_CHANNEL", "30"))

# --- Admin ---
# Comma-separated Telegram user IDs allowed to /addchannel, /removechannel
ADMIN_USER_IDS = set(
    int(x.strip()) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()
)

# --- Categories ---
VALID_CATEGORIES = {
    "markets",
    "crypto",
    "geopolitics",
    "tech",
    "macro",
    "oil_energy",
    "cybersecurity",
    "finance",
    "region",
    "other",
}

# Human-readable labels for display
CATEGORY_LABELS = {
    "markets":      "📈 Markets / Finance",
    "crypto":       "₿  Crypto / Web3",
    "geopolitics":  "🌍 Geopolitics",
    "tech":         "💻 Tech / AI",
    "macro":        "📊 Macro / Inflation",
    "oil_energy":   "🛢  Oil & Energy",
    "cybersecurity":"🔒 Cybersecurity",
    "finance":      "💰 Finance",
    "region":       "📍 Regional News",
    "other":        "📰 Other",
}

# --- Regions (sub-tag for region category) ---
VALID_REGIONS = {"india", "middle_east", "us", "europe", "asia", "africa", "latam", "global"}
