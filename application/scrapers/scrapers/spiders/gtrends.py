# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import re
import sys

from redis import Redis
from scrapy.exceptions import CloseSpider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.items import GtrendsItem
    from application.scrapers.scrapers.middlewares import GtrendsRequest
    from application.scrapers.scrapers.models import Gtrends
    from application.scrapers.scrapers.settings import ScrapeType
    from application.scrapers.scrapers.utils import multi_replace, split_list
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.items import GtrendsItem
    from scrapers.middlewares import GtrendsRequest
    from scrapers.models import Gtrends
    from scrapers.settings import ScrapeType
    from scrapers.utils import multi_replace, split_list


class GtrendsSpider(ArticleSpider):
    name = "gtrends"
    allowed_domains = ["trends.google.com"]

    def start_requests(self):
        self._keywords = self.settings.get("GTRENDS_KEYWORDS", ["bitcoin", "ethereum", "dash"])
        if len(self._keywords) == 0:
            raise CloseSpider("Keywords list is empty")
        # Redis
        self._redis = Redis(self.settings.get("REDIS_HOST"), self.settings.get("REDIS_PORT"))
        webui_db_uri = self.settings.get("WEBUI_DATABASE_URI", None)
        if webui_db_uri is not None:
            engine = create_engine(webui_db_uri)
            DBSession = sessionmaker(bind=engine)
            self._webui_db = DBSession()
        results_dir = self.settings.get("RESULTS_DIR", None)
        self._job_id = self.settings.get("JOB_ID", None)
        self._task_id = self.settings.get("TASK_ID", None)
        self.logger.info("Job ID {}, Task ID = {}".format(self._job_id, self._task_id))
        mongo_uri = self.settings.get("MONGO_URI", None)
        mongo_db = self.settings.get("MONGO_DB", None)
        keywords_lists = [self._keywords[i:i+5] for i in range(0, len(self._keywords), 5)]
        # print(keywords_lists)

        return [
            GtrendsRequest(
                keywords=kl
            )
            for kl in keywords_lists
        ]

    def parse(self, response):
        results = response.related_queries
        for keyword in self._keywords:
            if keyword in results:
                item = GtrendsItem()
                item["Keyword"] = keyword
                related_queries = []
                for k, v in results[keyword]["top"].to_dict()["query"].items():
                    related_queries.append(v)
                item["Related_Queries"] = related_queries
                yield item
