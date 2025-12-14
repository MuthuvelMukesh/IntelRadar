# Antigravity Telegram AI Info Agent

A Windows-compatible Telegram bot that fetches news from channels and web sources, categorizes them using an LLM, and provides summaries on demand.

## Features

- **Sources**: Fetches messages from configured Telegram channels and generic JSON APIs.
- **AI-Powered**: Uses an LLM to categorize, tag, and summarize content.
- **Database**: Stores all items in a local SQLite database (`news_bot.db`).
- **Bot Interface**: Interact via Telegram commands (`/update`, `/today`, `/category`).
- **Pluggable**: Designed for easy addition of new sources and LLM providers.

## Setup on Windows

### 1. Prerequisites
- **Python 3.10+**: Download and install from [python.org](https://www.python.org/downloads/). Ensure you check "Add Python to PATH" during installation.

### 2. Create a Virtual Environment
Open a terminal (Command Prompt or PowerShell) in the project directory:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configuration
1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` in a text editor and fill in your values:
   - **Telegram API Credentials**: Go to [my.telegram.org](https://my.telegram.org) to get `TG_API_ID` and `TG_API_HASH`.
   - **Bot Token**: Message [@BotFather](https://t.me/BotFather) on Telegram to create a bot and get `TG_BOT_TOKEN`.
   - **LLM Credentials**: Enter your OpenAI-compatible API key and Base URL.

## How to Run

Make sure your virtual environment is activated, then run:

```powershell
python -m antigravity_bot.runner
```

## How to Use

1. Start a chat with your bot on Telegram.
2. Send `/start` to see available commands.
3. Send `/update` to fetch new items from sources (this may take a moment).
4. Send `/today` to see categorized news from the last 24 hours.
5. Send `/category <name>` (e.g., `/category crypto`) to filter by topic.
