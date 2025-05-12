import os
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

if not BOT_TOKEN or not CHANNEL_USERNAME:
    raise ValueError("BOT_TOKEN or CHANNEL_USERNAME is not set in environment variables.")

bot = Bot(token=BOT_TOKEN)

try:
    bot.send_message(chat_id=CHANNEL_USERNAME, text="🚀 Bot integration successful!")
    print("✅ Message sent successfully.")
except Exception as e:
    print(f"❌ Failed to send message: {e}")
