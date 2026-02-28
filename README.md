# 🛰 Antigravity News Bot

A Telegram bot that monitors channels, classifies news with AI, and delivers personalized digests — filtered by category, region, and importance.

---

## ✨ Features

| Feature | Details |
|---|---|
| **10 categories** | Markets, Crypto, Geopolitics, Tech/AI, Macro, Oil/Energy, Cybersecurity, Finance, Regional, Other |
| **AI classification** | Every message is auto-classified, tagged, summarized, and rated 0–10 importance via OpenRouter (free) |
| **Morning digest** | AI-written narrative digest sent daily at 6:00 AM UTC |
| **Per-user subscriptions** | Each user picks their own categories via inline keyboard |
| **Dynamic channel management** | Admins add/remove channels live via `/addchannel` |
| **Auto-fetch** | Pulls new messages every 30 minutes in the background |
| **On-demand commands** | `/today`, `/digest`, `/category` for instant access |

---

## 🚀 Setup

### 1. Prerequisites

- Python 3.10+
- A Telegram account (for Telethon user API)
- A Telegram bot token (from @BotFather)
- A free OpenRouter account

### 2. Install

```bash
git clone <repo>
cd antigravity-bot

# The package directory MUST be named antigravity_bot (no spaces/hyphens)
# If your folder has a different name, rename it:
# mv "files (2)" antigravity_bot

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `TG_API_ID` / `TG_API_HASH` | [my.telegram.org](https://my.telegram.org) → API development tools |
| `TG_BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather) → /newbot |
| `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) → Keys (free account) |
| `ADMIN_USER_IDS` | Your Telegram user ID — get it from [@userinfobot](https://t.me/userinfobot) |

### 4. First Run

```bash
python -m antigravity_bot.runner
```

On first launch, Telethon will prompt you to log in to your Telegram account (phone + SMS code). This creates `antigravity_session.session` — keep it safe.

---

## 💬 Bot Commands

### For all users
| Command | Description |
|---|---|
| `/start` | Welcome message + command list |
| `/today` | All news from last 24h (filtered by your subscriptions) |
| `/digest [category]` | AI-written narrative digest. e.g. `/digest crypto` |
| `/category [name]` | Latest 20 items in a category. e.g. `/category tech` |
| `/subscribe` | Tap to choose your categories (inline keyboard) |
| `/myprefs` | View your current subscription settings |
| `/channels` | List all monitored channels |

### Admin only
| Command | Description |
|---|---|
| `/update` | Force-fetch new messages now |
| `/addchannel @username` | Add a Telegram channel to monitor |
| `/removechannel @username` | Stop monitoring a channel |

---

## 📂 Category Reference

| Key | Label |
|---|---|
| `markets` | 📈 Markets / Finance |
| `crypto` | ₿ Crypto / Web3 |
| `geopolitics` | 🌍 Geopolitics |
| `tech` | 💻 Tech / AI |
| `macro` | 📊 Macro / Inflation |
| `oil_energy` | 🛢 Oil & Energy |
| `cybersecurity` | 🔒 Cybersecurity |
| `finance` | 💰 Finance |
| `region` | 📍 Regional News |
| `other` | 📰 Other |

---

## 🏗 Architecture

```
antigravity_bot/
├── config.py       — All settings loaded from .env
├── models.py       — SQLAlchemy models (NewsItem, MonitoredChannel, UserSubscription)
├── db.py           — Database engine + session factory
├── llm.py          — OpenRouter API client (classify + digest generation)
├── fetcher.py      — Telethon client — pulls messages from channels
├── bot.py          — All Telegram command handlers
├── scheduler.py    — Periodic fetch + morning digest jobs
└── runner.py       — Entry point, wires everything together
```

**Database:** SQLite (`antigravity.db`) — no external DB needed.

**LLM Model:** `meta-llama/llama-3.3-70b-instruct:free` via OpenRouter — excellent at classification and summarization, free tier available.

---

## 🔧 Customization

- **Change digest time:** Set `DIGEST_HOUR=8` in `.env` for 8 AM UTC
- **Fetch frequency:** `FETCH_INTERVAL_MINUTES=15` for more frequent updates
- **Switch LLM model:** Change `OPENROUTER_MODEL` in `.env` to any model on [openrouter.ai/models](https://openrouter.ai/models)

---

## ⚠️ Notes

- Telethon reads channels as a **user account** (not the bot). The session file must be kept on the server.
- OpenRouter free tier has rate limits. The fetcher has a 1-second sleep between LLM calls to stay within limits.
- The bot stores all news in `antigravity.db`. Back this up periodically.
