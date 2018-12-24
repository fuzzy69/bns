# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import json
import re
import sys
from urllib.parse import quote

from scrapy import Request

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.utils import cleanup_html, multi_replace
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.utils import cleanup_html, multi_replace


class BitcoinSpider(ArticleSpider):
    """news.bitcoin.com article spider"""
    name = "bitcoin"
    start_urls = [
        "https://news.bitcoin.com/category/featured/",
        "https://news.bitcoin.com/category/economy-regulation/",
        "https://news.bitcoin.com/category/technology-security/",
        "https://news.bitcoin.com/category/market-updates/",
        "https://news.bitcoin.com/category/editorial-announcements/",
    ]
    pagination_xpath = "//div[contains(@class, 'page-nav')]//a/@href"
    article_xpath = "//div[@class='td-big-grid-wrapper' or @class='td-ss-main-content']//h3/a"  # 12 (2 fixed + 10)
    # articles per page

    def _parse_article_text(self, response):
        """Override"""
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = self._extract_meta(response, response.meta["item"])
        item["Site_Name"] = self.__class__.name
        # Extract article from scraped HTML
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        html = response.xpath("//div[@class='td-post-content']").extract_first()
        if html:
            item["Content_HTML"] = cleanup_html(html)
        # Extract data
        item = self._extract_data(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))
        comments_embed_url = self._extract_comments_embed_url(response.text)
        if not comments_embed_url:
            self.logger.info("Failed extracting comments url from \"{}\"".format(item["URL"]))
            yield item
        else:
            yield Request(comments_embed_url, self._extract_comments, meta={"item": item})

    def _extract_data(self, response, item):
        """Override"""
        item["Author"] = response.xpath("//div[contains(@class, 'td-author-name')]//a/text()").extract_first()
        item["Author_Profile"] = response.xpath("//div[contains(@class, 'td-author-name')]//a/@href").extract_first()
        total_views = response.xpath("//span[contains(@class, 'nr-views')]/text()").re("[0-9]+")
        if total_views:
            item["Total_Views"] = int(total_views[0])
        item["Comments"] = {}
        item["Shares"] = {}

        return item

    def _extract_comments_embed_url(self, text):
        """
        Extract URL to embeded comments
        :param text: HTML string
        :return: URL string
        """
        matches = re.search(r"var\s+embedVars\s+=\s+\{(.*?)\};", text)  # FIX Deprecation warnings on 3.6
        if not matches:
            return None
        data = json.loads('{' + matches.group(1) + '}')
        qs = []
        qs.append("base=default")
        qs.append("f=bitcoincom")
        qs.append("t_i={}".format(data["disqusIdentifier"]))
        qs.append("t_u={}".format(data["disqusUrl"]))
        title = quote(data["disqusTitle"])
        qs.append("t_e={}".format(title))
        qs.append("t_d={}".format(title))
        qs.append("t_t={}".format(title))
        qs.append("s_o=default")
        url = "https://disqus.com/embed/comments/?" + '&'.join(qs)

        return url

    def _extract_comments(self, response):
        """
        Extract disqus comments and yield results as scrapy item
        :param Response response: scrapy response
        :return: yields ArticleItem
        """
        item = response.meta["item"]
        self.logger.info("Extracting comments from \"{}\"".format(item["URL"]))
        json_data = response.xpath("//script[@id='disqus-threadData']/text()").extract_first()
        if json_data:
            data = json.loads(json_data)
            for comment in data["response"]["posts"]:
                user = multi_replace(comment["author"]["name"], {'.': '', '$': ''})
                datetime = parser.parse(comment["createdAt"]).isoformat()
                if user in item["Comments"]:
                    item["Comments"][user].update({
                        datetime: comment["raw_message"],
                    })
                else:
                    item["Comments"].update({
                        user: {
                            datetime: comment["raw_message"],
                        },
                    })
        else:
            self.logger.info("No comments found for \"{}\"".format(item["URL"]))

        yield item
