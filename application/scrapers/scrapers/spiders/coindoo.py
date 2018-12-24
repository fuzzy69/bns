# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import sys

try:
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.items import ArticleItem
    from application.scrapers.scrapers.models import Articles
    from application.scrapers.scrapers.settings import ScrapeType
    from application.scrapers.scrapers.utils import cleanup_html, multi_replace, init_custom_log
except ImportError:
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.items import ArticleItem
    from scrapers.models import Articles
    from scrapers.settings import ScrapeType
    from scrapers.utils import cleanup_html, multi_replace, init_custom_log


class CoindooSpider(ArticleSpider):
    """coindoo.com article spider"""
    name = "coindoo"
    start_urls = [
        "https://coindoo.com/category/news/",
    ]
    pagination_xpath = "//div[@class='pagination']/a/@href"
    article_xpath = "//div[contains(@class, 'main-body')]//a[contains(@class, 'poster-image')]"  # 10 articles per page

    def _extract_data(self, response, item):
        item["Author"] = response.xpath("//a[contains(@title, 'Posts by')]/text()").extract_first()
        item["Author_Profile"] = response.xpath("//a[contains(@title, 'Posts by')]/@href").extract_first()
        item["Total_Views"] = None
        item["Comments"] = None
        item["Shares"] = None
        item["Site_Name"] = self.__class__.name
        xpath = "//div[@class='entry-content']"
        els = response.xpath(xpath).extract()
        if els:
            html = ''.join(els)
            item["Content_HTML"] = self._cleaner.clean_html(html)
            # item["Content_HTML"] = cleanup_html(html)

        return item

    def _parse_article_text(self, response):
        """
        Extract meta data and article text from response object
        :param response: scrapy response object
        :yields: ArticleItem
        """
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = ArticleItem()
        item = self._extract_meta(response, item)
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        item["Content_HTML"] = ''
        item = self._extract_data(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))

        yield item

    def _extract_meta(self, response, item):
        """
        Extract metadata from article HTML string
        :param response: scrapy response object
        :param ArticleItem item: scrapy item
        :return: return ArticleItem
        """
        item["Language"] = response.xpath("//meta[@property='og:locale']/@content").extract_first()
        item["Type"] = response.xpath("//meta[@property='og:type']/@content").extract_first()
        title = response.xpath("//title/text()").extract_first()
        item["Title"] = title.split(" - Coindoo")[0] if title else title
        item["Description"] = response.xpath("//meta[@name='description']/@content").extract_first()
        item["URL"] = response.url
        item["Site_Name"] = response.xpath("//meta[@property='og:site_name']/@content").extract_first()
        item["Publisher"] = response.xpath("//meta[@property='article:publisher']/@content").extract_first()
        item["Author_FB"] = response.xpath("//meta[@property='article:author']/@content").extract_first()
        item["Tags"] = response.xpath("//div[@class='tags']/a/text()").extract()
        item["Section"] = response.xpath("//meta[@property='article:section']/@content").extract_first()
        Date_Published = response.xpath("//div[@class='mt-single-post-date']/text()").extract_first()
        item["Date_Published"] = parser.parse(Date_Published).isoformat() if Date_Published else None
        Date_Modified = response.xpath("//meta[@property='article:modified_time']/@content").extract_first()
        item["Date_Modified"] = parser.parse(Date_Modified).isoformat() if Date_Modified else None
        item["Headline_Image"] = response.xpath("//div[@itemprop='image']/meta[@itemprop='url']/@content").extract_first()
        item["Twitter_Description"] = response.xpath("//meta[@name='twitter:description']/@content").extract_first()
        item["Twitter_Title"] = response.xpath("//meta[@name='twitter:title']/@content").extract_first()
        item["Twitter_Site"] = response.xpath("//meta[@name='twitter:site']/@content").extract_first()
        item["Twitter_Image"] = response.xpath("//meta[@name='twitter:image']/@content").extract_first()
        item["Twitter_Creator"] = response.xpath("//meta[@name='twitter:creator']/@content").extract_first()

        return item
