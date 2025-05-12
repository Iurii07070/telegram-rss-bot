import os
# ====================
# 🔧 CONFIGURATION
# ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

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

FETCH_INTERVAL_MINUTES = 10
bot = Bot(token=BOT_TOKEN)
posted_links = set()

# ====================
# 🔁 MAIN FUNCTION
# ====================
def fetch_and_post():
    logger.info("Checking RSS feeds...")
    current_time = datetime.now(pytz.UTC)
    cutoff_time = current_time - timedelta(hours=5)
    summary_counts = {}

    for name, feed_url in FEEDS.items():
        logger.info(f"Fetching feed: {feed_url}")
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            try:
                if hasattr(entry, 'published_parsed'):
                    published = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)
                    if published < cutoff_time:
                        continue

                    link = entry.link
                    if link in posted_links:
                        continue

                    entry_time = time.mktime(entry.published_parsed)
                    if time.time() - entry_time > 600:
                        continue
                else:
                    continue

                title = html.unescape(entry.title)
                summary = html.unescape(getattr(entry, 'summary', ''))

                summary_sentences = []
                try:
                    if summary:
                        sentences = sent_tokenize(summary)
                        if len(sentences) > 3:
                            words = word_tokenize(summary.lower())
                            stop_words = set(stopwords.words('english') + list(punctuation))
                            word_freq = {
                                word: words.count(word)
                                for word in set(words)
                                if word.isalnum() and word not in stop_words
                            }
                            sent_scores = {
                                sent: sum(word_freq.get(word, 0) for word in word_tokenize(sent.lower()))
                                for sent in sentences
                            }
                            summary_sentences = nlargest(3, sent_scores, key=sent_scores.get)
                            summary = ' '.join(summary_sentences)
                except Exception as e:
                    logger.error(f"NLTK summarization error: {e}")

                image_url = None
                if 'media_content' in entry:
                    image_url = next((media['url'] for media in entry.media_content if 'url' in media), None)
                elif 'media_thumbnail' in entry:
                    image_url = entry.media_thumbnail[0]['url']

                translator = Translator()
                try:
                    russian_title = translator.translate(title, dest='ru').text
                    russian_summary = translator.translate(summary, dest='ru').text if summary else ''
                    russian_text = f"*{russian_title}*\n\n{russian_summary}"
                except Exception as e:
                    logger.error(f"Translation error: {e}")
                    russian_text = "_[Перевод недоступен]_"

                message = f"*{title}*\n\n{summary[:200] + '...' if len(summary) > 200 else summary}\n\n{russian_text[:200] + '...' if len(russian_text) > 200 else russian_text}\n\n[Читать полностью]({link})"

                if len(message) > 1024:
                    message = message[:1020] + "..."

                try:
                    if image_url:
                        bot.send_photo(
                            chat_id=CHANNEL_USERNAME,
                            photo=image_url,
                            caption=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        bot.send_message(
                            chat_id=CHANNEL_USERNAME,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    posted_links.add(link)
                    summary_counts[name] = summary_counts.get(name, 0) + 1
                    logger.info(f"Posted: {title}")
                    time.sleep(1)
                except TelegramError as e:
                    if "Flood control exceeded" in str(e):
                        logger.warning("Flood control exceeded. Retrying in 30 seconds...")
                        time.sleep(30)
                        continue
                    else:
                        logger.error(f"Telegram error: {e}")
            except Exception as e:
                logger.error(f"Error processing entry: {e}")
                continue

    # Log summary of fetched posts
    summary_text = "\n📊 Summary of fetched posts:\n"
    for source, count in summary_counts.items():
        summary_text += f"- {source}: {count} new post(s)\n"
    logger.info(summary_text)
    # Optionally, send to Telegram:
    # bot.send_message(chat_id=CHANNEL_USERNAME, text=summary_text)

# ====================
# 🕒 SCHEDULER SETUP
# ====================
def main():
    logger.info("Starting Telegram RSS bot...")
    fetch_and_post()
    scheduler = BlockingScheduler()
    scheduler.add_job(fetch_and_post, 'interval', minutes=FETCH_INTERVAL_MINUTES)
    scheduler.start()

if __name__ == '__main__':
    main()
