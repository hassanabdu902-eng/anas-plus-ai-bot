import os
import json
import time
from pathlib import Path

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

CONFIG_FILE = "wormgpt_config.json"
PROMPT_FILE = "system-prompt.txt"
USER_LANG_FILE = "user_langs.json"

DEVELOPER_NAME = "Anas Plus"
DEFAULT_LANGUAGE = "English"

MODEL_CONFIG = {
    "name": os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat"),
    "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    "key": os.getenv("OPENROUTER_KEY"),
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_1_LINK = os.getenv("CHANNEL_1_LINK", "https://t.me/+sC4ahEl_9atlZWY8").strip()
CHANNEL_2_LINK = os.getenv("CHANNEL_2_LINK", "https://t.me/+b3189Y-wlAs0Zjg0").strip()
CHANNEL_1_ID = os.getenv("CHANNEL_1_ID", "").strip()
CHANNEL_2_ID = os.getenv("CHANNEL_2_ID", "").strip()
REQUIRED_CHANNEL_IDS = [x for x in (CHANNEL_1_ID, CHANNEL_2_ID) if x]

FLOOD_DELAY = 3
LAST_MESSAGE_TIME = {}

def load_prompt():
    path = Path(PROMPT_FILE)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return (
        "You are Anas Plus AI, a helpful professional assistant. "
        "Answer in English only and provide safe, educational assistance."
    )

BASE_PROMPT = load_prompt()

USER_LANGS = {}
try:
    if Path(USER_LANG_FILE).exists():
        USER_LANGS = json.loads(Path(USER_LANG_FILE).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    USER_LANGS = {}

def save_user_langs():
    Path(USER_LANG_FILE).write_text(
        json.dumps(USER_LANGS, indent=2),
        encoding="utf-8"
    )

def get_user_lang(user_id):
    # English-only build
    return DEFAULT_LANGUAGE

def make_system_prompt():
    return (
        BASE_PROMPT
        + "\n\nImportant: Respond in English only. "
        + f"Your developer is {DEVELOPER_NAME}."
        + "\nAlways end your final response with exactly:\n"
        + f"{DEVELOPER_NAME}"
    )

def footer():
    return f"\n\n{DEVELOPER_NAME}"

async def verify_channels(user_id, bot):
    """Verify membership in configured channels. Channel IDs are required for private channels."""
    if not REQUIRED_CHANNEL_IDS:
        return True
    for channel_id in REQUIRED_CHANNEL_IDS:
        member = await bot.get_chat_member(channel_id, user_id)
        if member.status not in ("member", "administrator", "creator"):
            return False
    return True


def join_keyboard():
    rows = []
    if CHANNEL_1_LINK:
        rows.append([InlineKeyboardButton("Join Channel 1", url=CHANNEL_1_LINK)])
    if CHANNEL_2_LINK:
        rows.append([InlineKeyboardButton("Join Channel 2", url=CHANNEL_2_LINK)])
    rows.append([InlineKeyboardButton("I Joined - Verify", callback_data="verify_channels")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if REQUIRED_CHANNEL_IDS:
        try:
            if not await verify_channels(update.effective_user.id, context.bot):
                await update.message.reply_text(
                    "You must join both required channels before using this bot.",
                    reply_markup=join_keyboard()
                )
                return
        except Exception:
            await update.message.reply_text(
                "I could not verify channel membership. Make sure the bot is a member/admin of the required channels and that the channel IDs are correct."
            )
            return

    bot_user = await context.bot.get_me()
    context.bot_data["username"] = bot_user.username or ""

    await update.message.reply_text(
        "Welcome to Anas Plus AI.\n\n"
        "Professional English-only AI assistant.\n"
        "Developer: Anas Plus\n\n"
        "Send me a message to begin."
    )


async def joined_force_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not REQUIRED_CHANNEL_IDS:
        await query.edit_message_text(
            "Channel verification is not configured yet. Set CHANNEL_1_ID and CHANNEL_2_ID, then send /start again."
        )
        return

    try:
        if not await verify_channels(query.from_user.id, context.bot):
            await query.edit_message_text(
                "You have not joined both required channels yet.",
                reply_markup=join_keyboard()
            )
            return
        await query.edit_message_text("Verified. Send /start again to begin.")
    except Exception:
        await query.edit_message_text(
            "Verification failed. Check the channel IDs and bot permissions."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    bot_username = context.bot_data.get("username", "")
    user_id = update.effective_user.id
    user_msg = update.message.text
    chat_type = update.message.chat.type

    now = time.time()
    last = LAST_MESSAGE_TIME.get(user_id, 0)
    if now - last < FLOOD_DELAY:
        await update.message.reply_text("Please wait a few seconds before sending another message.")
        return
    LAST_MESSAGE_TIME[user_id] = now

    if chat_type in ("group", "supergroup"):
        if not user_msg.startswith("/") and bot_username:
            if f"@{bot_username.lower()}" not in user_msg.lower():
                return

    if not MODEL_CONFIG["key"]:
        await update.message.reply_text(
            "OpenRouter is not configured. Set the OPENROUTER_KEY environment variable."
        )
        return

    payload = {
        "model": MODEL_CONFIG["name"],
        "messages": [
            {"role": "system", "content": make_system_prompt()},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {MODEL_CONFIG['key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/",
        "X-Title": "Anas Plus AI",
    }

    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    try:
        response = requests.post(
            f"{MODEL_CONFIG['base_url'].rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()

        # Guarantee the requested developer signature.
        reply = reply.rstrip()
        if not reply.endswith(DEVELOPER_NAME):
            reply += footer()

    except requests.RequestException as exc:
        reply = f"OpenRouter request failed: {exc}{footer()}"
    except (KeyError, ValueError, TypeError) as exc:
        reply = f"Unexpected API response: {exc}{footer()}"
    except Exception as exc:
        reply = f"Unexpected error: {exc}{footer()}"

    # Telegram has a message length limit.
    if len(reply) <= 4096:
        await update.message.reply_text(reply)
    else:
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i:i + 4096])

async def setlang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "This build is English-only. No language selection is required."
    )

def build_app():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not set.")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setlang", setlang_cmd))
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(joined_force_callback, pattern="^verify_channels$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    return app

def run_bot():
    print(f"Anas Plus AI is running with {MODEL_CONFIG['name']}")
    build_app().run_polling()

if __name__ == "__main__":
    run_bot()
