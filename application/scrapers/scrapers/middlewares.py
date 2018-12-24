# -*- coding: utf-8 -*-

import logging
from random import choice

from scrapy import signals
from scrapy.exceptions import CloseSpider
from scrapy.http import Request, Response

from pytrends.request import TrendReq
import requests
import twitter


logger = logging.getLogger(__name__)


class ScrapersSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Response, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ScrapersDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class RotatingUserAgentMiddleware:
    """
    Rotate user agent on each request
    """

    def __init__(self, user_agents):
        """

        :param list user_agents: list of browser user agent strings
        """
        # print(user_agents)
        self._enabled = True if user_agents else False
        self._user_agents = user_agents
        # self._proxies = {}

    @classmethod
    def from_crawler(cls, crawler):
        user_agents = crawler.settings.get("USER_AGENTS")

        return cls(user_agents)

    def process_request(self, request, spider):
        if self._enabled:
            # if "proxy" in request.meta:
            #     proxy = request.meta["proxy"]
            #     if proxy in self._proxies:
            #         user_agent = self._proxies[proxy]
            #     else:
            #         user_agent = choice(self._user_agents)
            #         self._proxies[proxy] = user_agent
            # else:
            #     user_agent = choice(self._user_agents)
            user_agent = choice(self._user_agents)
            logger.debug(user_agent)
            # request.headers["User-Agent"] = user_agent
            # request.headers["User-Agent"] = user_agent
            # print(user_agent)
            # print(self._proxies)
            request.headers.setdefault("user-agent", user_agent)


class RotatingHttpProxyMiddleware:
    """
    Rotate proxies to avoid website ip ban
    """

    def __init__(self, proxies, proxy_max_retry):
        self._enabled = True if proxies else False
        self._proxies = {}
        self._load_proxies(proxies)
        self._proxy_max_retry = proxy_max_retry

    @classmethod
    def from_crawler(cls, crawler):
        proxies = crawler.settings.get("PROXIES")
        proxy_max_retry = crawler.settings.get("PROXY_MAX_RETRY")

        return cls(proxies, proxy_max_retry)

    def process_request(self, request, spider):
        if self._enabled:
            if len(self._proxies) == 0:
                raise CloseSpider("No available proxies")
            proxy = self._random_proxy()
            logger.info("Using proxy {} to request {}".format(proxy, request.url))
            request.meta["proxy"] = proxy

    def process_response(self, request, response, spider):
        if response.status in (500, 502, 503, 504, 400, 403, 404, 408):  # Try again
            return request

        return response  # :-(

    #  TODO Remove burned proxies
    def process_exception(self, request, exception, spider):
        if "proxy" in request.meta:
            proxy = request.meta["proxy"]
            self._proxies[proxy] += 1
            if self._proxies[proxy] >= self._proxy_max_retry:
                del request.meta["proxy"]
                del self._proxies[proxy]
                logger.info("Removing proxy {}".format(proxy))
            request.meta["exception"] = True
            if len(self._proxies) == 0:
                # self._enabled = False
                logger.info("Proxies depleted")
                raise CloseSpider("All proxies failed")

            return request

    def _load_proxies(self, proxies):
        for proxy in proxies:
            self._proxies[proxy] = 0

    def _random_proxy(self):
        proxies = list(self._proxies.keys())
        proxy = choice(proxies)

        return proxy


class TwitterRequest(Request):
    """
    """
    def __init__(self, *args, **kwargs):
        # print(args)
        # print(kwargs)
        # self.users = kwargs.pop("users", None)
        # self.keywords = kwargs.pop("keywords", None)
        self.query = kwargs.pop("query", None)
        # if "url" not in kwargs:
        #     kwargs["url"] = "http://twitter.com"
        # if "dont_filter" not in kwargs:
        #     kwargs["dont_filter"] = True
        kwargs["url"] = "http://twitter.com"
        kwargs["dont_filter"] = True
        super(TwitterRequest, self).__init__(
            **kwargs
        )

        # if "dont_filter" in kwargs:
        #     super(TwitterSearchRequest, self).__init__(
        #         'http://twitter.com',
        #         **kwargs
        #     )
        # else:
        #     super(TwitterSearchRequest, self).__init__(
        #         'http://twitter.com',
        #         dont_filter=True,
        #         **kwargs
        #     )


class TwitterResponse(Response):
    """
    """
    def __init__(self, *args, **kwargs):
        self.tweets = kwargs.pop('tweets', None)
        super(TwitterResponse, self).__init__(
            'http://twitter.com',
            *args,
            **kwargs
        )


class TwitterDownloaderMiddleware:
    """
    """
    def __init__(self,
                 consumer_key, consumer_secret,
                 access_token_key, access_token_secret):
        self._api = twitter.Api(consumer_key=consumer_key,
                               consumer_secret=consumer_secret,
                               access_token_key=access_token_key,
                               access_token_secret=access_token_secret)
        # logger.warning(self._api.VerifyCredentials())
        # raise CloseSpider("Done.")
        logger.info('Using creds [CONSUMER KEY: %s, ACCESS TOKEN KEY: %s]' %
                (consumer_key, access_token_key))

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        consumer_key = settings['TWITTER_CONSUMER_KEY']
        consumer_secret = settings['TWITTER_CONSUMER_SECRET']
        access_token_key = settings['TWITTER_ACCESS_TOKEN_KEY']
        access_token_secret = settings['TWITTER_ACCESS_TOKEN_SECRET']
        return cls(consumer_key,
                   consumer_secret,
                   access_token_key,
                   access_token_secret)

    def process_request(self, request, spider):
        # query = "q={}%20from%3A{}".format("%20OR%20".join(request.keywords), "%20OR%20from%3A".join(request.users))
        tweets = self._api.GetSearch(raw_query=request.query)
        # for t in tweets:
            # logger.warning(t.AsDict())

        return TwitterResponse(tweets=[t.AsDict() for t in tweets])
        # if isinstance(request, TwitterUserTimelineRequest):
        #     tweets = self.api.GetUserTimeline(screen_name=request.screen_name,
        #                                       count=request.count,
        #                                       max_id=request.max_id)
        #     return TwitterResponse(tweets=[tweet.AsDict() for tweet in tweets])

        # if isinstance(request, TwitterStreamFilterRequest):
        #     tweets = self.api.GetStreamFilter(track=request.track)
        #     return TwitterResponse(tweets=tweets)

    def process_response(self, request, response, spider):
        return response


class GtrendsRequest(Request):
    """
    Google Trends
    """
    def __init__(self, *args, **kwargs):
        self.keywords = kwargs.pop("keywords", None)
        kwargs["url"] = "https://trends.google.com/"
        kwargs["dont_filter"] = True
        super(GtrendsRequest, self).__init__(
            **kwargs
        )


class GtrendsResponse(Response):
    """
    """
    def __init__(self, *args, **kwargs):
        self.related_queries = kwargs.pop("related_queries", None)
        super(GtrendsResponse, self).__init__(
            "https://trends.google.com/",
            *args,
            **kwargs
        )


class GtrendsDownloaderMiddleware:
    """
    """
    def __init__(self, proxies=None):
        self._proxies = proxies
        if self._proxies:
            proxie = choice(self._proxies)
            pytrends = TrendReq(hl='en-US', tz=360, proxies = {"https": proxie})
        else:
            self._trends = TrendReq(hl='en-US', tz=360)

    @classmethod
    def from_crawler(cls, crawler):
        proxies = crawler.settings.get("PROXIES")

        return cls(proxies)

    def process_request(self, request, spider):
        self._trends.build_payload(kw_list=request.keywords)
        related_queries = self._trends.related_queries()

        return GtrendsResponse(related_queries=related_queries)

    def process_response(self, request, response, spider):
        return response
