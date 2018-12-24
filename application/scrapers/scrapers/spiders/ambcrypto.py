# -*- coding: UTF-8 -*-
#!/usr/bin/env python

import sys

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.utils import cleanup_html
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.utils import cleanup_html


class AmbcryptoSpider(ArticleSpider):
    """ambcrypto.com article spider"""
    name = "ambcrypto"
    start_urls = [
        "https://ambcrypto.com/category/news/",
        "https://ambcrypto.com/category/technology/",
        "https://ambcrypto.com/category/bitcoin-news/",
        "https://ambcrypto.com/category/altcoins-news/",
        "https://ambcrypto.com/category/xrp-ripple-news/",
    ]
    pagination_xpath = "//div[@class='pagination']/a/@href"
    article_xpath = "//li[contains(@class, 'blog-story')]/a"  # 10 articles per page

    def _extract_data(self, response, item):
        """Override"""
        item["Author"] = response.xpath("//div[contains(@class, 'td-author-name')]//a/text()").extract_first()
        item["Author_Profile"] = response.xpath("//div[contains(@class, 'td-author-name')]//a/@href").extract_first()
        item["Total_Views"] = None
        item["Comments"] = None
        item["Shares"] = None
        item["Site_Name"] = self.__class__.name
        html = response.xpath("//div[@id='mvp-content-main']").extract_first()
        if html:
            item["Content_HTML"] = cleanup_html(html)

        return item
