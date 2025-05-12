import os
import logging
import feedparser
import time
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

if not BOT_TOKEN or not CHANNEL_USERNAME:
    logger.error("Missing BOT_TOKEN or CHANNEL_USERNAME in environment variables")
    exit(1)

bot = Bot(token=BOT_TOKEN)

def fetch_and_send():
    logger.info("Fetching RSS feed...")
    feed = feedparser.parse("https://rss.cnn.com/rss/cnn_topstories.rss")
    for entry in feed.entries[:1]:  # Send only the latest entry for demo
        message = f"{entry.title}\n{entry.link}"
        bot.send_message(chat_id=CHANNEL_USERNAME, text=message)
        logger.info("Message sent")
        break

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_send, 'interval', minutes=5)
scheduler.start()

logger.info("Bot is running...")

while True:
    time.sleep(1)
