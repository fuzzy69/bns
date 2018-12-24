# -*- coding: utf-8 -*-

from json import loads, JSONDecodeError
import logging
import os
import sys

from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline
from mongoengine import connect, DoesNotExist

try:
    from application.scrapers.scrapers.exporters import CustomJsonItemExporter
    from application.scrapers.scrapers.items import ArticleItem, MarketItem, TwitterItem, GtrendsItem
    from application.scrapers.scrapers.models import Articles, Market, Twitter, Gtrends
except ImportError:
    sys.path.append("..")
    from scrapers.exporters import CustomJsonItemExporter
    from scrapers.items import ArticleItem, MarketItem, TwitterItem, GtrendsItem
    from scrapers.models import Articles, Market, Twitter, Gtrends


logger = logging.getLogger(__name__)


class ExtractArticlePipeline:
    pass


class CustomImagesPipeline(ImagesPipeline):

    def get_media_requests(self, item, info):
        logger.info("Scraping image \"{}\"".format(item["Headline_Image"]))
        yield Request(item["Headline_Image"])

    def item_completed(self, results, item, info):
        images = [x for ok, x in results if ok]
        if images:
            logger.info("Image from \"{}\" saved as \"{}\"".format(item["URL"], images[0]["path"]))

        return item


class MongoDBPipeline:
    """
    Pipeline for saving scraped data to MongoDB
    """
    collection_name = "articles"

    def __init__(self, mongo_uri, mongo_db):
        """

        :param str mongo_uri: Connection url
        :param str mongo_db: Database name
        """
        self._mongo_uri = mongo_uri
        self._mongo_db = mongo_db
        self._client = None
        self._db = None
        self._conn = None

    @classmethod
    def from_crawler(cls, crawler):
        """

        :param crawler:
        :return:
        """
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_db=crawler.settings.get("MONGO_DB"),
        )

    def open_spider(self, spider):
        """

        :param spider:
        :return:
        """
        self._conn = connect(self._mongo_db, host=self._mongo_uri)

    def close_spider(self, spider):
        """

        :param spider:
        :return: None
        """
        self._conn.close()

    def process_item(self, item, spider):
        """

        :param item:
        :param spider:
        :return: scrapy Item
        """
        if isinstance(item, ArticleItem):
            try:
                Articles.objects.get(URL=item["URL"])
                logger.info("Article \"{}\" already exists, skipping ...".format(item["URL"]))
                return item
            except DoesNotExist:
                article = Articles(**dict(item))
                article.save()
                logger.info("Successfully added article \"{}\" to MongoDB".format(item["URL"]))
            except Exception as e:
                logger.error("Failed saving to MongoDB, details: {}".format(e))
        elif isinstance(item, MarketItem):
            try:
                m = Market(**dict(item))
                m.save()
                logger.info("Successfully added market data for \"{}\" to MongoDB".format(item["Currency"]))
            except Exception as e:
                logger.error("Failed saving to MongoDB, details: {}".format(e))
        elif isinstance(item, TwitterItem):
            try:
                Twitter.objects.get(Tweet_ID=item["Tweet_ID"])
                logger.info("Tweet \"{}\" already exists, skipping ...".format(item["Tweet_ID"]))
                return item
            except DoesNotExist:
                t = Twitter(**dict(item))
                t.save()
                logger.info("Successfully added twitter data to MongoDB")
            except Exception as e:
                logger.error("Failed saving to MongoDB, details: {}".format(e))
        elif isinstance(item, GtrendsItem):
            try:
                Gtrends.objects.get(Keyword=item["Keyword"])
                logger.info("Trend keyword \"{}\" already exists, skipping ...".format(item["Keyword"]))
                return item
            except DoesNotExist:
                t = Gtrends(**dict(item))
                t.save()
                logger.info("Successfully added trend data for \"{}\" to MongoDB".format(item["Keyword"]))
            except Exception as e:
                logger.error("Failed saving to MongoDB, details: {}".format(e))
        else:
            logger.error("MongoDB Pipeline unsupported item type: {}".format(type(item)))

        return item


class CustomJSONPipeline:
    """
    """
    def __init__(self, file_name):
        self._file_name = file_name
        self._file_handle = None
        self._urls = set()
        self._exporter = None

    @classmethod
    def from_crawler(cls, crawler):
        file_name = crawler.settings.get("CUSTOM_FEED_URI")
        # file_name = crawler.settings.get("FEED_URI")

        return cls(file_name)

    def open_spider(self, spider):
        if os.path.isfile(self._file_name):
            logger.info("Loading JSON results \"{}\" file ...".format(self._file_name))
            file_contents = ''
            data = {}
            items = []
            with open(self._file_name, 'r') as f:
                for line in f.readlines():
                    if line.strip():
                        items.append(line.strip())
                # file_contents = f.read().strip().rstrip(',')
            try:
                # data = loads('[' + file_contents + ']')
                data = loads('[' + ','.join(items) + ']')
            except JSONDecodeError as e:
                logger.error("Failed parsing \"{}\" file".format(self._file_name))
                # exit()
            for item in data:
                self._urls.add(item["URL"])
        file = open(self._file_name, "ab")
        self._file_handle = file
        self._exporter = CustomJsonItemExporter(file)
        self._exporter.start_exporting()

    def close_spider(self, spider):
        logger.info("Custom JSON Exporter closed")
        self._exporter.finish_exporting()
        self._file_handle.close()

    def process_item(self, item, spider):
        if not "URL" in item or item["URL"] not in self._urls:
            self._exporter.export_item(item)

        return item
