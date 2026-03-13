# near-market-telegram-bot

Telegram bot for interacting with [market.near.ai](https://market.near.ai).

## Features

- 📋 `/jobs` — browse open jobs with inline buttons
- 🔍 Job details with one click
- 💼 Place bids directly from Telegram
- 💰 `/wallet` — check your NEAR balance
- 💼 `/bids` — view your active bids
- 🛠 `/services` — browse available services

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export BOT_TOKEN=your_telegram_bot_token
export AM_API_KEY=sk_live_your_market_api_key
```

3. Run:
```bash
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show main menu |
| `/jobs` | List open jobs |
| `/wallet` | Check NEAR balance |
| `/bids` | View your bids |
| `/services` | Browse services |

## API

Uses [market.near.ai/v1](https://market.near.ai/v1) with Bearer token auth.
