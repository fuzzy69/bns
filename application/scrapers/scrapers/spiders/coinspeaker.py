# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import json
import re
import sys
from urllib.parse import quote

from scrapy import Request
from scrapy.exceptions import CloseSpider

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


class CoinspeakerSpider(ArticleSpider):
    """coinspeaker.com article spider"""
    name = "coinspeaker"
    start_urls = [
        "https://www.coinspeaker.com/category/news/",
    ]
    pagination = "https://www.coinspeaker.com/category/news/page/3000/"
    pagination_xpath = "//div[contains(@class, 'pagination')]//a[contains(@class, 'page-numbers')]/@href"
    article_xpath = "//div[@class='newsTitle']/h3/a"  # 10 articles per page

    # def parse(self, response):
    #     pagination_xpath = "//div[contains(@class, 'pagination')]//a[contains(@class, 'page-numbers')]/@href"
    #     article_xpath = "//h3/a"
    #     parse_article_callback = self._parse_article_text
    #     if self._scrape_type == ScrapeType.UNSCRAPED:
    #         articles = self._unscraped_article_urls
    #         self.logger.info("Scraping {} unscraped articles ...".format(len(articles)))
    #     else:
    #         self.logger.info("Scraping article urls from \"{}\"".format(response.url))
    #         articles = response.xpath(article_xpath)
    #         self.logger.info("Found {} articles on \"{}\"".format(len(articles), response.url))
    #     for i, article in enumerate(articles):
    #         if self._scrape_type == ScrapeType.UNSCRAPED:
    #             article_url = article
    #         else:
    #             article_url = article.xpath("./@href").extract_first()
    #         if article_url in self._scraped_articles_urls:
    #             self.logger.info("Skipping already scraped article \"{}\"".format(article_url))
    #             continue
    #         item = ArticleItem()
    #         if self._scrape_test:
    #             self.logger.info("Scraping article \"{}\" ...".format(article_url))
    #         else:
    #             yield Request(article_url, parse_article_callback, meta={"item": item})
    #             self._scraped_articles_urls.add(article_url)
    #             if article_url not in self._articles_urls:
    #                 self._redis.sadd("{}:urls".format(self.__class__.name), article_url)
    #     # Go to the next pagination page
    #     if self._scrape_type == ScrapeType.ALL:
    #         next_pages_url = response.xpath(pagination_xpath).extract()
    #         if next_pages_url is not None:
    #             for i, url in enumerate(next_pages_url):
    #                 if url in self._visited_pagination_urls:
    #                     continue
    #                 self.logger.info("Scraping next pagination page \"{}\"".format(url))
    #                 yield Request(url)
    #                 self._visited_pagination_urls.add(url)
    #                 break

    def _parse_article_text(self, response):
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = self._extract_meta(response, response.meta["item"])
        item["Site_Name"] = self.__class__.name
        # Extract article from scraped HTML
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        html = response.xpath("//div[@class='entry-content']").extract_first()
        if html:
            item["Content_HTML"] = self._cleaner.clean_html(html)
        # Extract data
        item = self._extract_data(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))
        comments_embed_url = self._extract_comments_embed_url(response.text)
        if comments_embed_url:
            yield Request(comments_embed_url, self._extract_comments, meta={"item": item})
        self.logger.info("Failed extracting comments url from \"{}\"".format(item["URL"]))

        yield item

    def _extract_data(self, response, item):
        item["Author"] = response.xpath("//a[contains(@title, 'Posts by')]/text()").extract_first()
        item["Author_Profile"] = response.xpath("//a[contains(@title, 'Posts by')]/@href").extract_first()
        total_views = response.xpath("//span[contains(@class, 'nr-views')]/text()").re("[0-9]+")
        if total_views:
            item["Total_Views"] = int(total_views[0])
        item["Comments"] = {}
        item["Shares"] = {}

        return item

    def _extract_comments_embed_url(self, text):
        matches = re.search(r"var\s+embedVars\s+=\s+\{(.*?)\};", text)  # FIX Deprecation warnings on 3.6
        if not matches:
            return None
        data = json.loads('{' + matches.group(1) + '}')
        qs = []
        qs.append("base=default")
        qs.append("f=coinspeaker")
        qs.append("t_i={}".format(quote(data["disqusIdentifier"])))
        qs.append("t_u={}".format(quote(data["disqusUrl"])))
        title = quote(data["disqusTitle"])
        qs.append("t_e={}".format(title))
        qs.append("t_d={}".format(title))
        qs.append("t_t={}".format(title))
        qs.append("s_o=default")
        url = "https://disqus.com/embed/comments/?" + '&'.join(qs) + "#version=0c224241a140a6ab1eaaa8366f477ea8"

        return url

    def _extract_comments(self, response):
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
