# -*- coding: UTF-8 -*-

import datetime
from dateutil import parser
from json import loads, JSONDecodeError
from os import path
import sys
from urllib.parse import urljoin

import lxml
from lxml.html.clean import Cleaner
from goose3 import Goose
from mongoengine import connect
from redis import Redis
from scrapy import Request, Spider, signals
from scrapy.exceptions import CloseSpider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from application.scrapers.scrapers.items import ArticleItem
    from application.scrapers.scrapers.models import Articles
    from application.scrapers.scrapers.settings import REDIS_HOST, REDIS_PORT, ScrapeType
    from application.models import Jobs, SpiderStatus
except ImportError:
    sys.path.append("..")  # allow imports from application directory
    from scrapers.items import ArticleItem
    from scrapers.models import Articles
    from scrapers.settings import REDIS_HOST, REDIS_PORT, ScrapeType


class ArticleSpider(Spider):
    """
    Base spider class
    """
    name = "articlespider"
    start_urls = []
    base_url = None
    pagination_xpath = None
    article_xpath = ''
    new_articles_limit = None
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        # crawler.signals.connect(spider.spider_opened, signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        # crawler.signals.connect(spider.request_scheduled, signals.request_scheduled)
        crawler.signals.connect(spider.response_received, signals.response_received)

        return spider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scrape_type = None
        self._scrape_test = None
        self._goose = Goose({"enable_image_fetching": False})
        # self._redis = Redis(REDIS_HOST, REDIS_PORT)  # FIXME
        self._visited_pagination_urls = set()
        self._articles_urls = set()  # FIXME store in redis set
        self._scraped_articles_urls = set()
        self._unscraped_article_urls = set()
        self._job_id = None
        self._task_id = None
        self._webui_db = None
        self._redis = None
        self._cleaner = Cleaner()
        self._cleaner.javascript = True
        self._cleaner.style = True

    def start_requests(self):
        # Redis
        self._redis = Redis(self.settings.get("REDIS_HOST"), self.settings.get("REDIS_PORT"))
        webui_db_uri = self.settings.get("WEBUI_DATABASE_URI", None)
        if webui_db_uri is not None:
            engine = create_engine(webui_db_uri)
            DBSession = sessionmaker(bind=engine)
            self._webui_db = DBSession()
        self._scrape_type = self.settings.get("SCRAPE_TYPE")
        self._scrape_test = self.settings.get("SCRAPE_TEST", False)
        results_dir = self.settings.get("RESULTS_DIR", None)
        self._job_id = self.settings.get("JOB_ID", None)
        self._task_id = self.settings.get("TASK_ID", None)
        self.logger.info("Job ID {}, Task ID = {}".format(self._job_id, self._task_id))
        for url in self._redis.smembers("{}:urls".format(self.__class__.name)):
            self._articles_urls.add(url.decode("utf-8"))
        json_articles_urls = set()
        mongo_articles_urls = set()
        # # Load article urls from JSON
        # file_name = self.settings.get("CUSTOM_FEED_URI", None)
        # # file_contents = ''
        feed_data = {}
        # items = []
        # if file_name and path.isfile(file_name):
        #     with open(file_name, 'r') as f:
        #         for line in f.readlines():
        #             # file_contents = f.read().strip().rstrip(',')
        #             if line.strip():
        #                 items.append(line.strip())
        #     try:
        #         # feed_data = loads('[' + file_contents + ']')
        #         feed_data = loads('[' + ','.join(items) + ']')
        #     except JSONDecodeError as e:
        #         self.logger.error("Failed parsing \"{}\" file".format(file_name))
        #     for item in feed_data:
        #         json_articles_urls.add(item["URL"])
        # Load scraped urls from mongo
        mongo_uri = self.settings.get("MONGO_URI", None)
        mongo_db = self.settings.get("MONGO_DB", None)
        # Load article urls from mongo
        if mongo_db is not None and mongo_uri is not None:
            db = connect(mongo_db, host=mongo_uri)
            for article in Articles.objects.all():
                mongo_articles_urls.add(article.URL)
            db.close()
        # Load scraped article urls
        if mongo_db is not None and feed_data:
            self._scraped_articles_urls = mongo_articles_urls & json_articles_urls
        elif feed_data:
            self._scraped_articles_urls = json_articles_urls
        elif mongo_db is not None:
            self._scraped_articles_urls = mongo_articles_urls
        self._visited_pagination_urls.update(self.__class__.start_urls)
        if self._scrape_type == ScrapeType.UNSCRAPED:
            self._unscraped_article_urls = self._articles_urls - self._scraped_articles_urls
            yield Request(self.__class__.start_urls[0], self.parse)
        else:
            for url in self.__class__.start_urls:
                yield Request(url, self.parse)

    def spider_closed(self, spider):
        """

        :param spider:
        :return:
        """
        if self._webui_db is not None:
            stats = spider.crawler.stats.get_stats()
            job = self._webui_db.query(Jobs).filter(Jobs.id == self._job_id).first()
            if job is None:
                self.logger.warning("Failed updating spider state for job id {}".format(self._job_id))
                return
            job.date_finished = datetime.datetime.now()
            if "item_scraped_count" in stats:
                job.items_scraped = stats["item_scraped_count"]
            if job.spider_status != SpiderStatus.CANCELED:
                job.spider_status = SpiderStatus.FINISHED
            self._webui_db.commit()
            self.logger.info("Updated spider state for job id {}".format(self._job_id))

    # def request_scheduled(self, request, spider):
    #     self.logger.warning('*' * 50)
        # if self._redis.sismember("{}:stop".format(self.__class__.name), self._task_id):
        #     raise CloseSpider("Requested spider task {} cancellation".format(self._task_id))

    def response_received(self, response, request, spider):
        # self.logger.warning('+' * 50)
        if self._redis.sismember("{}:stop".format(self.__class__.name), self._task_id):
            # raise CloseSpider("Requested spider task {} cancellation".format(self._task_id))
            self.crawler.engine.close_spider(spider, "Requested spider task {} cancellation".format(self._task_id))

    def _parse_article_text(self, response):
        """
        Extract meta data and article text from response object
        :param response: scrapy response object
        :yields: ArticleItem
        """
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = ArticleItem()
        item = self._extract_meta(response, item)
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        item["Content_HTML"] = ''
        item = self._extract_data(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))

        yield item

    def _extract_meta(self, response, item):
        """
        Extract metadata from article HTML string
        :param response: scrapy response object
        :param ArticleItem item: scrapy item
        :return: return ArticleItem
        """
        item["Language"] = response.xpath("//meta[@property='og:locale']/@content").extract_first()
        item["Type"] = response.xpath("//meta[@property='og:type']/@content").extract_first()
        item["Title"] = response.xpath("//meta[@property='og:title']/@content").extract_first()
        item["Description"] = response.xpath("//meta[@name='description']/@content").extract_first()
        item["URL"] = response.xpath("//meta[@property='og:url']/@content").extract_first()
        item["Site_Name"] = response.xpath("//meta[@property='og:site_name']/@content").extract_first()
        item["Publisher"] = response.xpath("//meta[@property='article:publisher']/@content").extract_first()
        item["Author_FB"] = response.xpath("//meta[@property='article:author']/@content").extract_first()
        item["Tags"] = response.xpath("//meta[@property='article:tag']/@content").extract()
        item["Section"] = response.xpath("//meta[@property='article:section']/@content").extract_first()
        Date_Published = response.xpath("//meta[@property='article:published_time']/@content").extract_first()
        item["Date_Published"] = parser.parse(Date_Published).isoformat() if Date_Published else None
        Date_Modified = response.xpath("//meta[@property='article:modified_time']/@content").extract_first()
        item["Date_Modified"] = parser.parse(Date_Modified).isoformat() if Date_Modified else None
        item["Headline_Image"] = response.xpath("//meta[@property='og:image']/@content").extract_first()
        item["Twitter_Description"] = response.xpath("//meta[@name='twitter:description']/@content").extract_first()
        item["Twitter_Title"] = response.xpath("//meta[@name='twitter:title']/@content").extract_first()
        item["Twitter_Site"] = response.xpath("//meta[@name='twitter:site']/@content").extract_first()
        item["Twitter_Image"] = response.xpath("//meta[@name='twitter:image']/@content").extract_first()
        item["Twitter_Creator"] = response.xpath("//meta[@name='twitter:creator']/@content").extract_first()

        return item

    def _extract_data(self, response, item):
        """
        Extract rest of the data (Author data, views, comments, shares), must implement in child classes
        :param response:
        :param item:
        :return:
        """
        raise NotImplementedError

    def parse(self, response):
        """
        :param Response response: scrapy Response object
        :return: yields scrapy Request object
        """
        # Articles
        if self._scrape_type == ScrapeType.UNSCRAPED:
            articles = self._unscraped_article_urls
            self.logger.info("Scraping {} unscraped articles ...".format(len(articles)))
        else:
            self.logger.info("Scraping article urls from \"{}\"".format(response.url))
            articles = response.xpath(self.__class__.article_xpath)
            # Limit number of new articles for scraping
            if self.__class__.new_articles_limit is not None:
                if self._scrape_type == ScrapeType.NEW:
                    articles = articles[:self.__class__.new_articles_limit]
            self.logger.info("Found {} articles on \"{}\"".format(len(articles), response.url))
        for i, article in enumerate(articles):
            if self._scrape_type == ScrapeType.UNSCRAPED:
                article_url = article
            else:
                article_url = article.xpath("./@href").extract_first()
            # Fix incomplete article urls
            if self.__class__.base_url is not None:
                if not article_url.startswith("http") or article_url.startswith('/'):
                    article_url = urljoin(self.__class__.base_url, article_url)
            # Check if article is already scraped
            if article_url in self._scraped_articles_urls:
                self.logger.info("Skipping already scraped article \"{}\"".format(article_url))
                continue
            item = ArticleItem()
            if self._scrape_test:  # Test
                self.logger.info("Scraping article \"{}\" ...".format(article_url))
            else:  # Production
                # Scrape article
                yield Request(article_url, self._parse_article_text, meta={"item": item})
                # Save scraped article URL
                self._scraped_articles_urls.add(article_url)
                if article_url not in self._articles_urls:
                    self._redis.sadd("{}:urls".format(self.__class__.name), article_url)
            # # Ripple
            # if self.__class__.new_articles_limit is not None:
            #     if self._scrape_type == ScrapeType.NEW:
            #         if i > self.__class__.new_articles_limit:
            #             break
        # Pagination
        if self.__class__.pagination_xpath is not None:
            # Go to the next pagination page
            if self._scrape_type == ScrapeType.ALL:
                next_pages_url = response.xpath(self.__class__.pagination_xpath).extract()
                if next_pages_url is not None:
                    for url in next_pages_url:
                        # Skip already visited pagination URLs
                        if url in self._visited_pagination_urls:
                            continue
                        self.logger.info("Scraping next pagination page \"{}\"".format(url))
                        # Scrape pagination page
                        yield Request(url)
                        self._visited_pagination_urls.add(url)
                        break
