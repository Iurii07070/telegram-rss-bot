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

FEEDS = {
    "La Vanguardia": "https://www.lavanguardia.com/rss/home.xml",
    "ABC España": "https://www.abc.es/rss/feeds/abc_espana.xml",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
    "El Confidencial": "https://rss.elconfidencial.com/espana/espana.xml",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx",
    "20 Minutos": "https://rss.20minutos.es/rss/espana/",
    "Eldiario.es": "https://www.eldiario.es/rss",
    "La Razón": "https://www.larazon.es/rss",
    "El Periódico": "https://www.elperiodico.com/rss",
    "ARA": "https://www.ara.cat/rss",
    "TV3": "https://www.ccma.cat/tv3/rss/",
    "La Vanguardia Catalunya": "https://www.lavanguardia.com/rss/catalunya.xml",
    "El Punt Avui": "https://www.elpuntavui.cat/rss",
    "Catalunya Ràdio": "https://www.catradio.cat/feed/"
}

# Init
bot = Bot(token=BOT_TOKEN, request=Request(con_pool_size=8))
translator = Translator()
sent_history = set()

# NLP setup
import nltk
nltk.download("punkt")

# Timezone
LOCAL_TZ = timezone("Europe/Madrid")


def summarize_text(text, max_sentences=2):
    sentences = sent_tokenize(html.unescape(text))
    return " ".join(sentences[:max_sentences])


# Parse feed and post
def fetch_and_send():
    global sent_history, post_log
    now = datetime.now(LOCAL_TZ)
    ten_minutes_ago = now - timedelta(minutes=10)

    new_posts_count = {}  # Move this inside the function

    for source_name, url in FEEDS.items():
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
                image_url = (
                    entry.get("media_content", [{}])[0].get("url") or
                    entry.get("media_thumbnail", [{}])[0].get("url")
                )
                if image_url:
                    bot.send_photo(
                        chat_id=CHANNEL_USERNAME,
                        photo=image_url,
                        caption=title,
                        parse_mode=ParseMode.HTML
                    )
                    time.sleep(1.5)  # Flood control
            except Exception as e:
                logging.warning(f"No image sent: {e}")

            bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            time.sleep(1.5)  # Flood control

            sent_history.add(unique_id)
            new_posts.append(entry)

        new_posts_count[source_name] = len(new_posts)

    # Post summary to console and Telegram
    summary_lines = [f"{source} → {count} post(s)" for source, count in new_posts_count.items()]
    summary_text = "\n".join(summary_lines)
    log_msg = f"📊 <b>RSS Summary</b> ({now.strftime('%Y-%m-%d %H:%M')}):\n\n{html.escape(summary_text)}"

    logging.info(f"Fetched new posts:\n{summary_text}")

    # Send to Telegram even if no new posts
    bot.send_message(
        chat_id=CHANNEL_USERNAME,
        text=log_msg,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

# Scheduler
scheduler = BackgroundScheduler(timezone=LOCAL_TZ)
scheduler.add_job(fetch_and_send, "interval", minutes=10)
scheduler.start()

# Run once immediately
fetch_and_send()

# Start bot loop
print("Bot is running...")
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("Bot stopped.")
