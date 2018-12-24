# -*- coding: utf-8 -*-

from enum import IntEnum
from os import path
from pathlib import Path


class ScrapeType(IntEnum):
    ALL, NEW, UNSCRAPED, TEST = range(4)


BOT_NAME = 'scrapers'

SPIDER_MODULES = ['scrapers.spiders']
NEWSPIDER_MODULE = 'scrapers.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scrapers (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 1
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'scrapers.middlewares.ScrapersSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'scrapers.middlewares.ScrapersDownloaderMiddleware': 543,
#}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'scrapers.pipelines.ScrapersPipeline': 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings

# Cache
HTTPCACHE_ENABLED = False
#HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

DOWNLOADER_MIDDLEWARES = {}
ITEM_PIPELINES = {}

# Dirs
SCRIPT_ROOT = str(Path(path.realpath(path.dirname(__file__))).parent.parent.parent)
DATA_DIR = path.join(SCRIPT_ROOT, "data")
LOG_DIR = path.join(SCRIPT_ROOT, "logs")
RESULTS_DIR = path.join(SCRIPT_ROOT, "results")
FILES_DIR = path.join(RESULTS_DIR, "files")
IMAGES_DIR = path.join(RESULTS_DIR, "images")

# User agents
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 " \
             "Safari/537.36"
USER_AGENTS_FILE = path.join(DATA_DIR, "user_agents.txt")
USER_AGENTS = []
if path.isfile(USER_AGENTS_FILE):
    with open(USER_AGENTS_FILE, 'r') as f:
        for line in f.readlines():
            USER_AGENTS.append(line.strip())
    DOWNLOADER_MIDDLEWARES.update({
        "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
        "scrapers.middlewares.RotatingUserAgentMiddleware": 300,
        "scrapers.middlewares.TwitterDownloaderMiddleware": 10,
        "scrapers.middlewares.GtrendsDownloaderMiddleware": 20,
    })

# Proxies
# PROXIES_FILE = path.join(DATA_DIR, "proxies.txt")
# if path.isfile(PROXIES_FILE):
#     ROTATING_PROXY_LIST_PATH = PROXIES_FILE
#     ROTATING_PROXY_BACKOFF_BASE = 30
#     ROTATING_PROXY_BACKOFF_CAP = 60
#     DOWNLOADER_MIDDLEWARES.update({
#         "rotating_proxies.middlewares.RotatingProxyMiddleware": 610,
#         "rotating_proxies.middlewares.BanDetectionMiddleware": 620,
#     })

# # Database
# MONGO_URI = "mongodb://localhost:27017"
# MONGO_DB = "bitcoin_news"
# ITEM_PIPELINES.update({
#     "scrapers.pipelines.MongoDBPipeline": 300,
# })
#
# Feeds
# FEEDS_DIR = path.join(RESULTS_DIR, "feeds")
# ITEM_PIPELINES.update({
#     "scrapers.pipelines.CustomJSONPipeline": 600,
# })
#
#
# # Images
# IMAGES_DIR = path.join(RESULTS_DIR, "images")
# ITEM_PIPELINES.update({
#     "scrapers.pipelines.CustomImagesPipeline": 800,
# })
#

SCRAPE_TEST = False
SCRAPE_TYPE = ScrapeType.ALL

# Celery
REDIS_HOST = "redis"
REDIS_PORT = 6379
# BROKER_URI = "amqp://dummy:dummy@10.0.3.92:5672"
# BACKEND_URI = "redis://{}:{}/0".format(REDIS_HOST, REDIS_PORT)

# Logging
LOG_LEVEL = "INFO"

# Testing
SCRAPE_TEST = True
SCRAPE_TYPE = ScrapeType.ALL
# SCRAPE_TYPE = ScrapeType.NEW
REDIS_HOST = "10.0.3.92"
LOG_LEVEL = "DEBUG"
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapers.middlewares.RotatingUserAgentMiddleware": 300,
    # "scrapers.middlewares.TwitterDownloaderMiddleware": 10,
    # "scrapers.middlewares.GtrendsDownloaderMiddleware": 20,
}
HTTPCACHE_ENABLED = False
CONCURRENT_REQUESTS_PER_DOMAIN = 3
