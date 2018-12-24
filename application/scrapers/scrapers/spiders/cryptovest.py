# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import sys
from urllib.parse import urljoin

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider


class CryptovestSpider(ArticleSpider):
    """cryptovest.com article spider"""
    name = "cryptovest"
    start_urls = [
        "https://cryptovest.com/news/",
    ]
    base_url = "https://cryptovest.com/news/"
    pagination_xpath = "//div[@id='pagination']//li/a/@href"
    article_xpath = "//div[@class='titleBlock']/a"  # 6 (+ 4 static on every page) articles per page

    def _extract_data(self, response, item):
        """Override"""
        item["Author"] = response.xpath("//span[@class='authorName']/a/text()").extract_first()
        author_profile = response.xpath("//span[@class='authorName']/a/@href").extract_first()
        item["Author_Profile"] = urljoin("https://cryptovest.com/", author_profile)
        item["Total_Views"] = None
        item["Comments"] = None
        item["Shares"] = None
        item["Site_Name"] = self.__class__.name
        xpath = "//div[position()=1 and contains(@class, 'post-content')]//*[self::p or self::h3]"
        els = response.xpath(xpath).extract()
        if els:
            html = ''.join(els)
            item["Content_HTML"] = self._cleaner.clean_html(html)

        return item

    # TODO: Comments
