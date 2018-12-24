# -*- coding: UTF-8 -*-

from os import path
import sys
from time import sleep, strftime

from scrapy import Request, Spider

try:
    # from application.scrapers.scrapers.articlescraper import ArticleScraper
    from application.scrapers.scrapers.items import ArticleItem
    from application.scrapers.scrapers.models import Articles
    from application.scrapers.scrapers.utils import cleanup_html, multi_replace
except ImportError:
    sys.path.append("..")  # allow imports from application directory
    # from scrapers.articlescraper import ArticleScraper
    from scrapers.items import ArticleItem
    from scrapers.models import Articles
    from scrapers.utils import cleanup_html, multi_replace


class TestSpider(Spider):
    name = "testspider"
    start_urls = [
        # "http://httpbin.org/ip",
        # "https://httpbin.org/ip",
        # "http://httpbin.org/headers",
        # "https://httpbin.org/headers",
        # "http://httpbin.org/user-agent",
        # "https://httpbin.org/user-agent",
        "http://localhost:7000/q",
        "http://localhost:7000/w",
        "http://localhost:7000/e",
        "http://localhost:7000/r",
        "http://localhost:7000/t",
    ]

    def parse(self, response):
        self.logger.info("Scraping article urls from \"{}\"".format(response.url))
        print(response.text)
        sleep(3)

        return {
            "URL": response.url,
            "status_code": response.status,
            "text": response.text,
        }

    def close(spider, reason):
        print("Done.")
