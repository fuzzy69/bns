# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import sys

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider


class BitcoinistSpider(ArticleSpider):
    """bitcoinist.com article spider"""
    name = "bitcoinist"
    start_urls = [
        "https://bitcoinist.com/category/news/",
    ]
    pagination_xpath = "//div[@class='pagination']//li/a/@href"
    article_xpath = "//h3[@class='title']/a"  # 27 articles per page

    def _extract_data(self, response, item):
        """Override"""
        item["Author"] = response.xpath("//span[@class='author']/a/text()").extract_first()
        item["Author_Profile"] = response.xpath("//span[@class='author']/a/@href").extract_first()
        item["Total_Views"] = None
        item["Comments"] = None
        item["Shares"] = None
        item["Site_Name"] = self.__class__.name
        xpath = "//article[position()=1 and contains(@id, 'post-')]/*[self::p or self::h3]"
        els = response.xpath(xpath).extract()
        if els:
            html = ''.join(els)
            item["Content_HTML"] = self._cleaner.clean_html(html)

        return item
