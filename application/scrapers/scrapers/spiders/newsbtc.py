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


class NewsbtcSpider(ArticleSpider):
    """newsbtc.com article spider"""
    name = "newsbtc"
    start_urls = [
        "https://www.newsbtc.com/category/bitcoin/",
        "https://www.newsbtc.com/category/altcoins/",
        "https://www.newsbtc.com/category/sponsored-stories/",
        "https://www.newsbtc.com/category/ico/",
        "https://www.newsbtc.com/category/blockchain-projects/",
        "https://www.newsbtc.com/category/crypto-tech/",
        "https://www.newsbtc.com/category/industry-news/",
        "https://www.newsbtc.com/press-releases",
        "https://www.newsbtc.com/category/analysis/",
    ]
    pagination_xpath = "//div[@class='pagination']//li/a/@href"
    article_xpath = "//article/a"  # 10 articles per page

    def _parse_article_text(self, response):
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = self._extract_meta(response, response.meta["item"])
        item["Title"] = item["Title"].strip(" | NewsBTC")
        item["Site_Name"] = self.__class__.name
        # Extract article from scraped HTML
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        html = response.xpath("//article").extract_first()
        if html:
            item["Content_HTML"] = self._cleaner.clean_html(html)
        # Extract data
        item = self._extract_data(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))
        comments_embed_url = self._extract_comments_embed_url(response.text)
        if not comments_embed_url:
            self.logger.info("Failed extracting comments url from \"{}\"".format(item["URL"]))
            yield item
        else:
            yield Request(comments_embed_url, self._extract_comments, meta={"item": item})

    def _extract_data(self, response, item):  # TODO
        author = response.xpath("//span[@class='meta large']/span[@class='author']/text()").extract_first()
        item["Author_Profile"] = None
        if author:
            author = author.strip()
            item["Author"] = author
            item["Author_Profile"] = response.xpath("//a[@title='Posts by {}']/@href".format(author)).extract_first()
        item["Total_Views"] = None
        item["Comments"] = {}
        item["Shares"] = {}

        return item

    def _extract_comments_embed_url(self, text):
        matches = re.search("var\s+embedVars\s+=\s+\{(.*?)\};", text)
        if not matches:
            return None
        data = json.loads('{' + matches.group(1) + '}')
        qs = []
        qs.append("base=default")
        qs.append("f=newsbtc")
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
