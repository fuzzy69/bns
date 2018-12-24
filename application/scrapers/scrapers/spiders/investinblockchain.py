# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import json
import requests
import sys

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.utils import cleanup_html, multi_replace
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.utils import cleanup_html, multi_replace


class InvestinblockchainSpider(ArticleSpider):
    """investinblockchain.com article spider"""
    name = "investinblockchain"
    start_urls = [
        "https://www.investinblockchain.com/category/news/",
        "https://www.investinblockchain.com/category/investment-opinion/",
        "https://www.investinblockchain.com/category/cryptocurrencies-platforms/",
        "https://www.investinblockchain.com/category/blockchain-basics/",
    ]
    pagination_xpath = "//div[@class='nav-links']//a[contains(@class, 'page-numbers')]/@href"
    article_xpath = "//h2[contains(@class, 'entry-title')]/a"  # 20 articles per page

    def _parse_article_text(self, response):
        """Override"""
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = self._extract_meta(response, response.meta["item"])
        item["Site_Name"] = self.__class__.name
        # Extract article from scraped HTML
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        xpath = "//article[contains(@id, 'post-')]/*[self::div[contains(@class, 'header-standard')] " \
                "or self::div[@class='post-image'] or self::div[contains(@class, 'post-entry')]]"
        els = response.xpath(xpath).extract()
        if els:
            html = ''.join(els)
            item["Content_HTML"] = cleanup_html(html)
        # Extract data
        item = self._extract_data(response, item)
        item = self._extract_comments(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))
        # Extract shares
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.investinblockchain.com",
            "pragma": "no-cache",
            "referer": item["URL"],
        }
        form_data = {
            "site_id": "97244e00ae264300afe3a200b9639400817c9d00120cdf000289c5004a37d000",
            "contentAnalyticsStatus": "true",
            "shareService": "true",
            "href": item["URL"],
            "urls[]": item["URL"],
        }
        # FIXME
        r = requests.post(
            "https://sumo.com/services",
            headers=headers,
            data=form_data,
        )
        try:
            data = json.loads(r.text)
            d = data["shareService"]
            item["Shares"] = {
                "twitter": int(d["twitter"]) if "twitter" in d else 0,
                "facebook": int(d["facebook"]) if "facebook" in d else 0,
                "google": int(d["googleplus"]) if "googleplus" in d else 0,
                "linkedin": int(d["linkedin"]) if "linkedin" in d else 0,
                "reddit": int(d["reddit"]) if "reddit" in d else 0,
                "email": int(d["email"]) if "email" in d else 0,
            }
        except Exception as e:
            pass

        return item

    def _extract_data(self, response, item):
        """Override"""
        item["Author"] = response.xpath("//a[@class='author-url']/text()").extract_first()
        item["Author_Profile"] = response.xpath("//a[@class='author-url']/@href").extract_first()
        item["Total_Views"] = None
        item["Comments"] = {}
        item["Shares"] = {}

        return item

    def _extract_comments(self, response, item):
        """Override"""
        comments = {}
        for comment in response.xpath("//div[@id='comments']//div[@class='thecomment']"):
            user = comment.xpath(".//span[@class='author']//text()").extract_first()
            if not user:
                continue
            datetime = comment.xpath(".//span[@class='date']/text()").extract_first()
            if not datetime:
                continue
            comment = comment.xpath(".//div[@class='comment-content']//text()").extract_first()
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
