# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from datetime import datetime
from re import sub
import sys
from urllib.parse import urljoin

from scrapy import Request

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.items import ArticleItem, MarketItem
    from application.scrapers.scrapers.models import Articles, Market
    from application.scrapers.scrapers.settings import ScrapeType
    from application.scrapers.scrapers.utils import multi_replace, string_to_float
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.items import ArticleItem, MarketItem
    from scrapers.models import Articles, Market
    from scrapers.settings import ScrapeType
    from scrapers.utils import multi_replace, string_to_float


class CoinmarketcapSpider(ArticleSpider):
    """coinmarketcap.com market data spider"""
    name = "coinmarketcap"
    start_urls = [
        "https://coinmarketcap.com/",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

    def parse(self, response):
        pagination_xpath = "//ul[contains(@class,'pagination')][1]//a[contains(text(), 'Next 100')]/@href"
        rows = response.xpath("//table//tr")
        for i, row in enumerate(rows):
            item = MarketItem()
            try:
                currency = row.xpath("./td[contains(@class, 'currency-name')]/@data-sort").extract_first()
                market_cap = row.xpath("./td[contains(@class, 'market-cap')]/text()").extract_first()
                price = row.xpath("./td/a[@class='price']/text()").extract_first()
                volume = row.xpath("./td/a[@class='volume']/@data-usd").extract_first()
                change = row.xpath("./td[contains(@class, 'percent-change')]/text()").extract_first()
                # print(currency)
                # print(market_cap)
                # print(price)
                # print(volume)
                # print(change)
                if not all((currency, market_cap, price, volume, change)):
                    continue
                item["Currency"] = currency
                item["Market_Capitalization"] = 0 if market_cap.strip() == '?' else string_to_float(market_cap)
                item["Price"] = string_to_float(price)
                item["Volume"] = 0 if volume.strip() == "None" else string_to_float(volume)
                item["Change"] = string_to_float(change)
                item["Date_Published"] = self._timestamp
            except Exception as e:
                self.logger.info("Failed parsing market data, details: {}".format(e))
                continue
            self.logger.info("Successfully scrape market data for \"{}\"".format(currency))
            yield item
        # Go to the next pagination page
        if self._scrape_type == ScrapeType.ALL:
            next_page_url = response.xpath(pagination_xpath).extract_first()
            if next_page_url is not None:
                    url = urljoin("https://coinmarketcap.com/", next_page_url)
                    self.logger.info("Scraping next pagination page \"{}\"".format(url))
                    yield Request(url)
