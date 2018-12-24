# -*- coding: UTF-8 -*-

from os import environ, path


__title__ = "Bitcoin News Scraper"
__description__ = "Scrapy based spider for scraping articles from bitcoin related news websites"
__version__ = (0, 4, 6, "180831")

# Setup ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
DELAY = 3  # seconds
TIMEOUT = 30  # seconds
RETRIES = 2
SCHEDULE_DELAY = 30  # minutes
RABBIT_HOST = environ.get("RABBIT_HOST", "10.0.3.92")
RABBIT_PORT = environ.get("RABBIT_PORT", 5672)
RABBIT_USER = environ.get("RABBIT_USER", "dummy")
RABBIT_PASS = environ.get("RABBIT_PASS", "dummy")
BROKER_URI = "amqp://{user}:{pwd}@{host}:{port}".format(
    host=RABBIT_HOST, port=RABBIT_PORT,
    user=RABBIT_USER, pwd=RABBIT_PASS,
)
REDIS_HOST = environ.get("REDIS_HOST", "10.0.3.92")
REDIS_PORT = int(environ.get("REDIS_PORT", 6379))
MONGO_URI = "mongodb://10.0.3.92:27017"
# MONGO_URI = "mongodb://mongo:27017"
MONGO_DB = "bitcoin_news"
WEBUI_HOST = environ.get("WEBUI_HOST", "127.0.0.1")
WEBUI_PORT = int(environ.get("WEBUI_PORT", 4000))
WEBUI_LOGGING = True
CELERY_LOGGING = True
# Setup ////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Do not change const values bellow
DEBUG = False
# DEBUG = True

FLASK_SECRET_KEY = "g%j+xKvK!-\+Xmh]]$c+8Rre~K#wYpYH"
IPP = 50  # Pagination items per page

DOWNLOADER_MIDDLEWARES = {}
ITEM_PIPELINES = {}

# Dirs
SCRIPT_ROOT = path.realpath(path.dirname(__file__))
DATA_DIR = path.join(SCRIPT_ROOT, "data")
LOG_DIR = path.join(SCRIPT_ROOT, "logs")
RESULTS_DIR = path.join(SCRIPT_ROOT, "results")
FILES_DIR = path.join(RESULTS_DIR, "files")
IMAGES_DIR = path.join(RESULTS_DIR, "images")

# Feeds
FEEDS_DIR = path.join(RESULTS_DIR, "feeds")

# User agents
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/63.0.3239.132 Safari/537.36"
USER_AGENTS_FILE = path.join(DATA_DIR, "user_agents.txt")
USER_AGENTS = []
if path.isfile(USER_AGENTS_FILE):
    with open(USER_AGENTS_FILE, 'r') as f:
        for line in f.readlines():
            USER_AGENTS.append(line.strip())

# Proxies
PROXIES_FILE = path.join(DATA_DIR, "proxies.txt")
ROTATING_PROXY_LIST_PATH = PROXIES_FILE
ROTATING_PROXY_BACKOFF_BASE = 30
ROTATING_PROXY_BACKOFF_CAP = 60

# Twitter
TWITTER_USERNAMES_FILE = path.join(DATA_DIR, "twitter_usernames.txt")
TWITTER_KEYWORDS_FILE = path.join(DATA_DIR, "twitter_keywords.txt")

# Extensions
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,  # Disable telnet console to avoid port errors
}

# Web UI
WEBUI_DATABASE_URI = "sqlite:///" + path.join(SCRIPT_ROOT, "data", "webui_2.db")
SETTINGS_FILE = path.join(SCRIPT_ROOT, "data", "settings.pickle")

# Spiders
SPIDERS = (
    ("ambcrypto", "https://ambcrypto.com/"),
    ("bitcoin", "https://news.bitcoin.com/"),
    ("bitcoinist", "https://bitcoinist.com/"),
    ("btcmanager", "https://btcmanager.com/"),
    ("coindoo", "https://coindoo.com/"),
    ("coinmarketcap", "https://coinmarketcap.com/"),
    ("coinspeaker", "https://www.coinspeaker.com/"),
    ("cryptoninjas", "https://www.cryptoninjas.net/"),
    ("cryptovest", "https://cryptovest.com/"),
    ("investinblockchain", "https://www.investinblockchain.com/"),
    ("newsbtc", "https://www.newsbtc.com/"),
    ("ripple", "https://ripple.com/"),
    ("twitter", "https://twitter.com/"),
    ("gtrends", "https://trends.google.com/"),

    # ("testspider", "https://httpbin.org/"),
)
