# Anas Plus AI Telegram Bot

English-only Telegram AI assistant powered by OpenRouter.

## Developer
Anas Plus

## Environment variables

- `TELEGRAM_TOKEN` — Telegram bot token
- `OPENROUTER_KEY` — OpenRouter API key
- `OPENROUTER_MODEL` — optional model override
- `OPENROUTER_BASE_URL` — optional API base URL
- `REQUIRED_CHANNEL` — optional Telegram channel such as `@YourChannel`

## Run

```bash
pip install -r requirements.txt
python main.py
```

The bot always responds in English and appends `Anas Plus` to responses.

Never put your API keys directly into source code or commit them to GitHub.


## Required channels
Two private invite links are configured as Join buttons. Telegram membership verification requires the actual channel IDs (`CHANNEL_1_ID` and `CHANNEL_2_ID`); invite links alone cannot be used with `get_chat_member`. Add the bot to both channels with sufficient permissions, then set the IDs in the environment.

## Security
The credentials supplied during setup were intentionally NOT embedded in this ZIP. Because bot/API credentials were shared in chat, rotate/revoke those credentials and create new ones before deployment. Put the new values in the deployment environment or `.env` file. Never publish them in source code.
