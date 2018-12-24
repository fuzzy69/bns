# -*- coding: UTF-8 -*-

from enum import IntEnum
from pickle import dump, load


class ScrapeType(IntEnum):
    ALL, NEW, UNSCRAPED = range(3)


class SpiderStatus(IntEnum):
    PENDING, RUNNING, FINISHED, CANCELED = range(4)


class JobEnabled(IntEnum):
    DISABLED, ENABLED = range(2)


class JobType(IntEnum):
    ONETIME, PERIODIC = range(2)


class UseProxies(IntEnum):
    NO, YES = range(2)


class OK(IntEnum):
    NO, YES = range(2)


class Settings:
    """

    """

    def __init__(self, delay=3, timeout=20, retries=2, concurrent_requests=1,
                 mongo_uri="mongodb://10.0.3.92:27017", mongo_db="bitcoin_news",
                 scrape_type=0, use_proxies=0,
                 feed=0, db=0, images=0):
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.concurrent_requests = concurrent_requests
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.scrape_type = scrape_type
        self.use_proxies = use_proxies
        self.feed = feed
        self.db = db
        self.images = images

    def to_dict(self):
        d = {}
        for attr in self.__dict__:
            # d[attr.upper()] = getattr(self, attr)
            d[attr] = getattr(self, attr)

        return d

    def save(self, file_path):
        with open(file_path, "wb") as f:
            dump(self, f)

    def load(self, file_path):
        s = None
        with open(file_path, "rb") as f:
            s = load(f)
        if s is not None:
            for attr in s.__dict__:
                setattr(self, attr, getattr(s, attr))

    def __str__(self):
        return str(self.__dict__)
