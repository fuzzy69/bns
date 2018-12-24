# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import datetime
import logging
from os import environ, path
from pprint import pprint
from time import sleep, strftime

from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import BROKER_URI, WEBUI_DATABASE_URI, LOG_DIR
from application.misc import SpiderStatus, ScrapeType
from application.models import Jobs, PeriodicJobs
from application.spiders import SPIDERS

from twisted.internet import asyncioreactor
asyncioreactor.install()
from billiard import Process
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging

from config import BROKER_URI, DEBUG, DOWNLOADER_MIDDLEWARES, EXTENSIONS, FEEDS_DIR, IMAGES_DIR, \
    ITEM_PIPELINES, LOG_DIR, MONGO_DB, MONGO_URI, ROTATING_PROXY_BACKOFF_BASE, ROTATING_PROXY_BACKOFF_CAP, \
    ROTATING_PROXY_LIST_PATH, USER_AGENT, USER_AGENTS, RESULTS_DIR, TWITTER_USERNAMES_FILE, TWITTER_KEYWORDS_FILE

# TODO: Cleanup imports

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

engine = create_engine(WEBUI_DATABASE_URI)
DBSession = sessionmaker(bind=engine)
db_session = DBSession()

app = Celery(
    "bns",
    broker=BROKER_URI,
    # backend=BACKEND_URI,
)


def crawler_process(params):
    """

    :param params:
    :return: None
    """
    spider = SPIDERS[params["spider"]]
    settings = Settings()
    crawler = CrawlerProcess(settings)
    # Global settings
    settings["BOT_NAME"] = "Bitcoin News Scraper [{}]".format(spider.name)
    settings["ROBOTSTXT_OBEY"] = False
    settings["COOKIES_ENABLED"] = False
    settings["CONCURRENT_REQUESTS"] = 1 if params["spider_name"] == "twitter" else params["concurrent_requests"]
    settings["DOWNLOAD_DELAY"] = 3 if params["spider_name"] == "twitter" else params["delay"]
    # settings["DOWNLOAD_DELAY"] = params["delay"]
    settings["DOWNLOAD_TIMEOUT"] = params["timeout"]
    settings["RETRY_TIMES"] = params["retries"]
    settings["USER_AGENT"] = USER_AGENT
    settings["LOG_LEVEL"] = "INFO"
    if USER_AGENTS:
        settings["USER_AGENTS"] = USER_AGENTS
        DOWNLOADER_MIDDLEWARES.update({
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "application.scrapers.scrapers.middlewares.RotatingUserAgentMiddleware": 300,
        })
    if params["use_proxies"]:
        settings["ROTATING_PROXY_BACKOFF_BASE"] = ROTATING_PROXY_BACKOFF_BASE
        settings["ROTATING_PROXY_BACKOFF_CAP"] = ROTATING_PROXY_BACKOFF_CAP
        settings["ROTATING_PROXY_LIST_PATH"] = ROTATING_PROXY_LIST_PATH
        DOWNLOADER_MIDDLEWARES.update({
            "rotating_proxies.middlewares.RotatingProxyMiddleware": 610,
            "rotating_proxies.middlewares.BanDetectionMiddleware": 620,
        })
    if params["db"]:
        settings["MONGO_DB"] = MONGO_DB if DEBUG else params["mongo_db"]
        settings["MONGO_URI"] = MONGO_URI if DEBUG else params["mongo_uri"]
        ITEM_PIPELINES.update({
            "application.scrapers.scrapers.pipelines.MongoDBPipeline": 300,
        })
    # Note: Do not enable images pipeline for coinmarketcap and twitter spider!
    if params["images"] and params["spider_name"] not in ("coinmarketcap", "gtrends", "twitter"):
        settings["IMAGES_STORE"] = path.join(IMAGES_DIR, spider.name)
        ITEM_PIPELINES.update({
            "application.scrapers.scrapers.pipelines.CustomImagesPipeline": 800,
        })
    # Spider specific settings
    if params["feed"]:
        settings["FEEDS_DIR"] = FEEDS_DIR
        settings["CUSTOM_FEED_URI"] = params["feed_file"]
        ITEM_PIPELINES.update({
            "application.scrapers.scrapers.pipelines.CustomJSONPipeline": 600,
        })
    if params["log"]:
        settings["LOG_FILE"] = params["log"]
    # Twitter
    if params["spider_name"] == "twitter":
        settings["TWITTER_CONSUMER_KEY"] = params["twitter_consumer_key"]
        settings["TWITTER_CONSUMER_SECRET"] = params["twitter_consumer_secret"]
        settings["TWITTER_ACCESS_TOKEN_KEY"] = params["twitter_access_token_key"]
        settings["TWITTER_ACCESS_TOKEN_SECRET"] = params["twitter_access_token_secret"]
        settings["TWITTER_USERS"] = []
        settings["TWITTER_KEYWORDS"] = []
        with open(TWITTER_USERNAMES_FILE, 'r') as f:
            for line in f.readlines():
                settings["TWITTER_USERS"].append(line.strip())
        with open(TWITTER_KEYWORDS_FILE, 'r') as f:
            for line in f.readlines():
                settings["TWITTER_KEYWORDS"].append(line.strip())
        DOWNLOADER_MIDDLEWARES.update({
            "application.scrapers.scrapers.middlewares.TwitterDownloaderMiddleware": 10,
        })
    # Gtrends
    if params["spider_name"] == "gtrends":
        settings["GTRENDS_KEYWORDS"] = []
        with open(TWITTER_KEYWORDS_FILE, 'r') as f:
            for line in f.readlines():
                settings["GTRENDS_KEYWORDS"].append(line.strip())
        DOWNLOADER_MIDDLEWARES.update({
            "application.scrapers.scrapers.middlewares.GtrendsDownloaderMiddleware": 11,
        })
        if params["use_proxies"]:
            PROXIES = []
            if path.isfile(ROTATING_PROXY_LIST_PATH):
                with open(ROTATING_PROXY_LIST_PATH, 'r') as f:
                    for line in f.readlines():
                        if line.strip().startswith("https"):
                            PROXIES.append(line.strip())
            settings["PROXIES"] = PROXIES
    settings["DOWNLOADER_MIDDLEWARES"] = DOWNLOADER_MIDDLEWARES
    settings["ITEM_PIPELINES"] = ITEM_PIPELINES
    settings["EXTENSIONS"] = EXTENSIONS
    settings["SCRAPE_TYPE"] = params["scrape_type"]
    settings["RESULTS_DIR"] = RESULTS_DIR
    settings["JOB_ID"] = params["job_id"]
    settings["TASK_ID"] = params["task_id"]
    settings["WEBUI_DATABASE_URI"] = WEBUI_DATABASE_URI
    settings["SCRAPE_TEST"] = DEBUG
    settings["REDIS_HOST"] = params["redis_host"]
    settings["REDIS_PORT"] = params["redis_port"]

    crawler.crawl(spider)
    crawler.start()


def run_crawler(params):
    """

    :param params:
    :return: process instance
    """
    process = Process(target=crawler_process, args=(params, ), )
    process.start()

    return process


@app.task
def run_job(job_id, params):
    """

    :param job_id:
    :param params:
    :return: None
    """
    # Update job
    job = db_session.query(Jobs).filter_by(id=job_id).first()
    if job is None:
        return False
    job.task_id = run_job.request.id
    time_stamp = datetime.datetime.now()
    job.date_started = time_stamp
    file_name = "{} {}".format(job.spider_name, time_stamp.strftime("%Y-%m-%d %H:%M:%S"))
    log_file = file_name + ".log"
    feed_file = file_name + ".json"
    job.spider_status = SpiderStatus.RUNNING
    db_session.commit()
    params["log"] = path.join(LOG_DIR, log_file)
    params["feed_file"] = path.join(FEEDS_DIR, feed_file)
    params["scrape_type"] = ScrapeType(params["scrape_type"])
    params["job_id"] = job_id
    params["task_id"] = job.task_id
    print(params)
    process = run_crawler(params)


@app.task
def run_periodic_job(job_id, params):
    """

    :param job_id:
    :param params:
    :return: None
    """
    time_stamp = datetime.datetime.now()
    file_name = "{} {}".format(params["spider_name"], time_stamp.strftime("%Y-%m-%d %H:%M:%S"))
    log_file = file_name + ".log"
    feed_file = file_name + ".json"
    job = Jobs(
        task_id=run_periodic_job.request.id,
        spider_name=params["spider_name"],
        spider_status=SpiderStatus.RUNNING,
        scrape_type=params["scrape_type"],
        use_proxies=params["use_proxies"],
        file=params["feed"],
        db=params["db"],
        images=params["images"],
        date_started=datetime.datetime.now(),
    )
    db_session.add(job)
    db_session.commit()
    params["log"] = path.join(LOG_DIR, log_file)
    params["feed_file"] = path.join(FEEDS_DIR, feed_file)
    params["scrape_type"] = ScrapeType(params["scrape_type"])
    params["job_id"] = job.id
    params["task_id"] = job.task_id
    print(params)
    process = run_crawler(params)


if __name__ == "__main__":
    logging.error("Starting Celery ...")
    logging.error(BROKER_URI)
    app.start()
