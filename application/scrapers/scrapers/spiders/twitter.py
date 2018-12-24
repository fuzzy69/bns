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
    from application.scrapers.scrapers.items import TwitterItem
    from application.scrapers.scrapers.middlewares import TwitterRequest
    from application.scrapers.scrapers.models import Twitter
    from application.scrapers.scrapers.settings import ScrapeType
    from application.scrapers.scrapers.utils import multi_replace
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.items import TwitterItem
    from scrapers.middlewares import TwitterRequest
    from scrapers.models import Twitter
    from scrapers.settings import ScrapeType
    from scrapers.utils import multi_replace


class TwitterSpider(ArticleSpider):
    name = "twitter"
    allowed_domains = ["twitter.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self._twitter_users = ["bitcoin", "coindesk", "ethereum"]
        # self._twitter_keywords = ["dash", "price"]

    def start_requests(self):
        # self._twitter_key = self.settings.get("TWITTER_CONSUMER_KEY", None)
        # self._twitter_secret = self.settings.get("TWITTER_CONSUMER_SECRET", None)
        # self._twitter_token_key = self.settings.get("TWITTER_ACCESS_TOKEN_KEY", None)
        # self._twitter_token_secret = self.settings.get("TWITTER_ACCESS_TOKEN_SECRET", None)
        self._twitter_users = self.settings.get("TWITTER_USERS", [])
        self._twitter_keywords = self.settings.get("TWITTER_KEYWORDS", [])
        # self.logger.error(self._twitter_users)
        # self.logger.error(self._twitter_keywords)
        if len(self._twitter_users) == 0 or len(self._twitter_keywords) == 0:
            raise CloseSpider("Twitter users/keywords lists are empty")
        # Redis
        self._redis = Redis(self.settings.get("REDIS_HOST"), self.settings.get("REDIS_PORT"))
        webui_db_uri = self.settings.get("WEBUI_DATABASE_URI", None)
        if webui_db_uri is not None:
            engine = create_engine(webui_db_uri)
            DBSession = sessionmaker(bind=engine)
            self._webui_db = DBSession()
        # self._scrape_type = self.settings.get("SCRAPE_TYPE")
        # self._scrape_test = self.settings.get("SCRAPE_TEST", False)
        # if self._scrape_test:
            # self.__class__.start_urls = self.__class__.start_urls[:1]
        results_dir = self.settings.get("RESULTS_DIR", None)
        self._job_id = self.settings.get("JOB_ID", None)
        self._task_id = self.settings.get("TASK_ID", None)
        self.logger.info("Job ID {}, Task ID = {}".format(self._job_id, self._task_id))
        # for url in self._redis.smembers("{}:urls".format(self.__class__.name)):
            # self._articles_urls.add(url.decode("utf-8"))
        mongo_uri = self.settings.get("MONGO_URI", None)
        mongo_db = self.settings.get("MONGO_DB", None)
        # Query
        queries = []
        keywords = list(map(lambda x: re.sub(r"\s+", "%20", x), self._twitter_keywords))
        query = "q={}%20from%3A{}".format("%20OR%20".join(keywords), "%20OR%20from%3A".join(self._twitter_users))
        limit = 499

        if len(query) > limit:
            for user in self._twitter_users:
                l = 0
                r = 1
                track = []
                while True and r < len(keywords):
                    query = "q={}%20from%3A{}".format("%20OR%20".join(keywords[l:r]), "%20OR%20from%3A".join([user]))
                    x = "{}-{}".format(l, r)
                    track.append(x)
                    if track.count(x) > 3:
                        break
                    # print(l, r)
                    # print(len(query), query)
                    if len(query) < limit:
                        r += 1
                        if r == len(keywords):
                            queries.append(query)
                            break
                    else:
                        queries.append("q={}%20from%3A{}".format("%20OR%20".join(keywords[l:r - 1]), "%20OR%20from%3A".join([user])))
                        l = r - 1
                        # r += 1
                        if r == len(keywords):
                            break
                    # time.sleep(1)
                # break
        else:
            queries.append(query)

        # search_requests = []
        # for user in self._twitter_users:
        #     query = "q={}%20from%3A{}".format("%20OR%20".join(self._twitter_keywords), "%20OR%20from%3A".join([user]))
        #     search_requests.append(
        #         TwitterSearchRequest(
        #             users=self._twitter_users,
        #             keywords=self._twitter_keywords,
        #             query=query,
        #         )
        #     )

        # return search_requests
        return [
            TwitterRequest(
                # users=self._twitter_users,
                # keywords=self._twitter_keywords,
                query=query,
            )
            for query in queries
        ]

    def parse(self, response):
        tweets = response.tweets
        for tweet in tweets:
            # self.logger.warning(tweet)
            item = TwitterItem()
            item["Tweet_ID"] = tweet["id"]
            item["User"] = tweet["user"]["screen_name"]
            item["Tweet"] = tweet["text"]
            item["Date_Published"] = parser.parse(tweet["created_at"]).isoformat()
            if "coordinates" in tweet:
                item["Longitude"], item["Latitude"] = tweet["coordinates"]["coordinates"]
            else:
                item["Longitude"] = None
                item["Latitude"] = None
            country = tweet["user"]["location"].split(',')
            if "place" in tweet:
                # country = country[-1].strip() if len(country) > 1 else None
                item["Country"] = tweet["place"]["country"]
            else:
                item["Country"] = None
            item["Language"] = tweet["lang"]
            # item["Language"] = tweet["user"]["lang"]
            yield item
            # break
