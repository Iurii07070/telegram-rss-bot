import os
import time
import feedparser
import logging
import html
from datetime import datetime, timedelta
from pytz import timezone, utc
from apscheduler.schedulers.background import BackgroundScheduler

from telegram import Bot, ParseMode
from telegram.utils.request import Request
from googletrans import Translator
from nltk.tokenize import sent_tokenize

# Setup
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
RSS_FEEDS = [
    'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada',
    'https://www.lavanguardia.com/rss/home.xml',
    'https://www.abc.es/rss/feeds/abc_espana.xml',
    'https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml',
    'https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml',
    'https://rss.elconfidencial.com/espana/espana.xml',
    'https://www.europapress.es/rss/rss.aspx',
    'https://rss.20minutos.es/rss/espana/',
    'https://www.eldiario.es/rss',
    'https://www.larazon.es/rss',
    'https://www.elperiodico.com/rss',
    'https://www.ara.cat/rss',
    'https://www.ccma.cat/tv3/rss/',
    'https://www.lavanguardia.com/rss/catalunya.xml',
    'https://www.elpuntavui.cat/rss',
    'https://www.catradio.cat/feed/'
]

# Init
bot = Bot(token=BOT_TOKEN, request=Request(con_pool_size=8))
translator = Translator()
sent_history = set()
post_log = {}

# NLP setup
import nltk
nltk.download("punkt")

# Timezone
LOCAL_TZ = timezone("Europe/Madrid")

# Format text and sanitize
def summarize_text(text, max_sentences=2):
    sentences = sent_tokenize(html.unescape(text))
    return " ".join(sentences[:max_sentences])

# Parse feed and post
def fetch_and_send():
    global sent_history, post_log
    now = datetime.now(LOCAL_TZ)
    ten_minutes_ago = now - timedelta(minutes=10)

    new_posts_count = {}

    for url in FEED_URLS:
        feed = feedparser.parse(url)
        new_posts = []

        for entry in feed.entries:
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if not published:
                continue

            published_dt = datetime.fromtimestamp(time.mktime(published), tz=utc).astimezone(LOCAL_TZ)
            if published_dt < ten_minutes_ago:
                continue

            unique_id = entry.get("id") or entry.get("link")
            if unique_id in sent_history:
                continue

            title = html.unescape(entry.get("title", "No Title"))
            description = html.unescape(entry.get("summary", ""))
            summary = summarize_text(description)
            translation = translator.translate(summary, src="es", dest="ru").text

            msg = f"📰 <b>{html.escape(title)}</b>\n\n" \
                  f"{html.escape(summary)}\n\n" \
                  f"🇷🇺 {html.escape(translation)}\n\n" \
                  f"🔗 <a href='{entry.link}'>Read More</a>"

            try:
                image_url = entry.get("media_content", [{}])[0].get("url") or entry.get("media_thumbnail", [{}])[0].get("url")
                if image_url:
                    bot.send_photo(chat_id=CHANNEL_USERNAME, photo=image_url, caption=title, parse_mode=ParseMode.HTML)
                    time.sleep(1.5)  # Flood control
            except Exception as e:
                logging.warning(f"No image sent: {e}")

            bot.send_message(chat_id=CHANNEL_USERNAME, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            time.sleep(1.5)  # Flood control

            sent_history.add(unique_id)
            new_posts.append(entry)

        new_posts_count[url] = len(new_posts)

    # Optional: Post summary of updates
    if any(new_posts_count.values()):
        summary_text = "\n".join([f"{url} → {count} post(s)" for url, count in new_posts_count.items()])
        logging.info(f"Fetched new posts:\n{summary_text}")

# Scheduler
scheduler = BackgroundScheduler(timezone=LOCAL_TZ)
scheduler.add_job(fetch_and_send, "interval", minutes=10)
scheduler.start()

# Start bot loop
print("Bot is running...")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("Bot stopped.")
