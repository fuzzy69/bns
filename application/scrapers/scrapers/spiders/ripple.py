# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import sys

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider


class RippleSpider(ArticleSpider):
    """ripple.com article spider"""
    name = "ripple"
    start_urls = [
        "https://ripple.com/category/insights/news/",
        "https://ripple.com/category/insights/views/",
        "https://ripple.com/category/insights/features/",
        "https://ripple.com/category/xrp/",
    ]
    article_xpath = "//h2[@class='entry-title']/a"  # all articles
    new_articles_limit = 5

    def _extract_data(self, response, item):
        """Override"""
        item["Author"] = response.xpath("//span[contains(@class, 'author')]/text()").extract_first()
        item["Author_Profile"] = None
        item["Total_Views"] = None
        item["Comments"] = None
        item["Shares"] = None
        item["Site_Name"] = self.__class__.name
        xpath = "//article//*[self::p]"
        els = response.xpath(xpath).extract()
        if els:
            html = ''.join(els)
            item["Content_HTML"] = self._cleaner.clean_html(html)
        item["Title"] = item["Title"].strip(" | Ripple")

        return item
