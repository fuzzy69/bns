# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import sys

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.items import ArticleItem
    from application.scrapers.scrapers.models import Articles
    from application.scrapers.scrapers.settings import ScrapeType
    from application.scrapers.scrapers.utils import multi_replace
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.items import ArticleItem
    from scrapers.models import Articles
    from scrapers.settings import ScrapeType
    from scrapers.utils import multi_replace


class CryptoninjasSpider(ArticleSpider):
    """cryptoninjas.net article spider"""
    name = "cryptoninjas"
    start_urls = [
        "https://www.cryptoninjas.net/news-archive/",
    ]
    pagination_xpath = "//nav[@id='load-more-posts']/a/@href"
    article_xpath = "//h2[@class='entry-title']/a"  # 15 articles per page

    def _extract_data(self, response, item):
        item["Author"] = response.xpath("//div[@class='news-source']/a/span/text()").extract_first()
        item["Author_Profile"] = response.xpath("//div[@class='news-source']/a/@href").extract_first()
        item["Total_Views"] = None
        item["Comments"] = None
        item["Shares"] = None
        item["Site_Name"] = self.__class__.name
        content_xpath = "//div[contains(@class, 'entry-content')]"
        els = response.xpath(content_xpath).extract()
        if els:
            html = ''.join(els)
            item["Content_HTML"] = self._cleaner.clean_html(html)
        item = self._extract_comments(response, item)

        return item

    def _extract_comments(self, response, item):
        comments = {}
        for comment in response.xpath("//div[contains(@id, 'comment-')]"):
            user = comment.xpath(".//div[contains(@class, 'wc-comment-author')]/text()").extract_first()
            if not user:
                continue
            # datetime = comment.xpath(".//span[@class='date']/text()").extract_first()
            # TODO: Fix comment datetime
            datetime = response.xpath("//time/text()").extract_first()
            if not datetime:
                continue
            comment = comment.xpath(".//div[@class='wc-comment-text']//text()").extract_first()
            if not comment:
                continue
            user = multi_replace(user, {'.': '', '$': ''})
            datetime = parser.parse(datetime).isoformat()
            if user in comments:
                comments[user].update({
                    datetime: comment,
                })
            else:
                comments.update({
                    user: {
                        datetime: comment,
                    },
                })
        item["Comments"] = comments

        return item
