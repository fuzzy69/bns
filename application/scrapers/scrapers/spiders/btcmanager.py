# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from dateutil import parser
import json
import re
import sys
from urllib.parse import quote

from lxml import html
from scrapy import Request
from scrapy.exceptions import CloseSpider

try:  # main
    from application.scrapers.scrapers.articlespider import ArticleSpider
    from application.scrapers.scrapers.items import ArticleItem
    from application.scrapers.scrapers.settings import ScrapeType
    from application.scrapers.scrapers.utils import multi_replace
except ImportError:  # scrapy crawl
    sys.path.append("..")  # allow imports from application directory
    from scrapers.articlespider import ArticleSpider
    from scrapers.items import ArticleItem
    from scrapers.settings import ScrapeType
    from scrapers.utils import multi_replace


class BtcmanagerSpider(ArticleSpider):
    """btcmanager.com article spider"""
    name = "btcmanager"
    start_urls = [
        "https://btcmanager.com/news/",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page = 0
        self._total_pages = 0
        self._nonce = None
        self._post_id = None
        self._pagination_url = "https://btcmanager.com/wp-admin/admin-ajax.php?action=alm_query_posts&nonce={}&" \
            "query_type=standard&post_id={}&" \
            "slug=bitcoin&canonical_url=https%3A%2F%2Fbtcmanager.com%2Fcategory%2Fnews%2Fbitcoin%2F&" \
            "cache_logged_in=false&repeater=default&theme_repeater=null&acf=&nextpage=&cta=&comments=&users=&" \
            "post_type%5B%5D=post&sticky_posts=&post_format=&category=Bitcoin&category__not_in=&tag=&tag__not_in=" \
            "&taxonomy=&taxonomy_terms=&taxonomy_operator=&taxonomy_relation=&meta_key=_featured-post&meta_value=1" \
            "&meta_compare=NOT+IN&meta_relation=&meta_type=&author=&year=&month=&day=&post_status=&order=DESC" \
            "&orderby=date&post__in=&post__not_in=&exclude=&search=&custom_args=" \
            "&posts_per_page=10&page={}&offset=10" \
            "&preloaded=false&seo_start_page=1&paging=false&previous_post=&lang="

    def parse(self, response):
        pagination_xpath = ""
        article_xpath = "//h2/a/@href"
        parse_article_callback = self._parse_article_text
        if self._scrape_type == ScrapeType.UNSCRAPED:
            articles = self._unscraped_article_urls
            self.logger.info("Scraping {} unscraped articles ...".format(len(articles)))
            for i, article_url in enumerate(articles):
                item = ArticleItem()
                yield Request(article_url, parse_article_callback, meta={"item": item})
                self._scraped_articles_urls.add(article_url)
                if article_url not in self._articles_urls:
                    self._redis.sadd("{}:urls".format(self.__class__.name), article_url)
                if self._redis.sismember("{}:stop".format(self.__class__.name), self._task_id):
                    raise CloseSpider("Requested spider task {} cancellation".format(self._task_id))
        else:
            self.logger.info("Scraping article urls from \"{}\"".format(response.url))
            pagination = response.meta["pagination"] if "pagination" in response.meta else False
            if not pagination:  # First page (HTML)
                articles = response.xpath(article_xpath).extract()
                matches = re.search(r'"alm_nonce":"(.*?)"', response.text)  # FIX Deprecation warnings on 3.6
                self._nonce = matches.group(1) if matches else None
                self._post_id = response.xpath("//div[@id='ajax-load-more']/@data-post-id").extract_first()
            else:  # The rest ones (JSON)
                data = json.loads(response.text)
                if self._total_pages == 0:
                    total_posts = (data["meta"]["totalposts"])
                    self._total_pages = int(total_posts) // 10
                dom = html.fromstring(data["html"])
                articles = dom.xpath(article_xpath)
            for i, article_url in enumerate(articles):
                if article_url in self._scraped_articles_urls:
                    self.logger.info("Skipping already scraped article \"{}\"".format(article_url))
                    continue
                item = ArticleItem()
                if self._scrape_test:
                    self.logger.info("Scraping article \"{}\" ...".format(article_url))
                else:
                    yield Request(article_url, parse_article_callback, meta={"item": item})
                    self._scraped_articles_urls.add(article_url)
                    if article_url not in self._articles_urls:
                        self._redis.sadd("{}:urls".format(self.__class__.name), article_url)
            # Go to the next pagination page
            if self._scrape_type == ScrapeType.ALL:
                if not pagination:  # First page (HTML)
                    pagination_url = self._get_pagination_url()
                    if pagination_url is not None:
                        yield Request(pagination_url, meta={"pagination": True})
                else:  # The rest ones (JSON)
                    self._page += 1
                    if self._page < self._total_pages + 1:
                        pagination_url = self._get_pagination_url()
                        if pagination_url is not None:
                            yield Request(pagination_url, meta={"pagination": True})

    def _get_pagination_url(self):
        if self._nonce is None or self._post_id is None:
            return None

        return self._pagination_url.format(self._nonce, self._post_id, self._page)

    def _parse_article_text(self, response):
        self.logger.info("Scraping article \"{}\" ...".format(response.url))
        item = self._extract_meta(response, response.meta["item"])
        item["Site_Name"] = self.__class__.name
        # Extract article from scraped HTML
        article = self._goose.extract(raw_html=response.text)
        item["Content_Body"] = article.cleaned_text
        html = response.xpath("//div[@itemprop='articleBody']").extract_first()
        if html:
            item["Content_HTML"] = self._cleaner.clean_html(html)
        # Extract data
        item = self._extract_data(response, item)
        self.logger.info("Successfully scraped \"{}\"".format(response.url))
        comments_embed_url = self._extract_comments_embed_url(response, item)
        # print('*' * 50)
        # print(comments_embed_url)
        if comments_embed_url:
            yield Request(comments_embed_url, self._extract_comments, meta={"item": item})
        else:
            self.logger.info("Failed extracting comments url from \"{}\"".format(item["URL"]))
            yield item

    def _extract_data(self, response, item):
        item["Author"] = response.xpath("//span[@itemprop='author']/a/text()").extract_first()
        item["Author_Profile"] = response.xpath("//span[@itemprop='author']/a/@href").extract_first()
        total_views = response.xpath("//span[contains(@class, 'nr-views')]/text()").re("[0-9]+")
        if total_views:
            item["Total_Views"] = int(total_views[0])
        item["Comments"] = {}
        item["Shares"] = {}

        return item

    def _extract_comments_embed_url(self, response, item):
        qs = []
        qs.append("base=default")
        qs.append("f=btcmanager")
        qs.append("t_u={}".format(quote(item["URL"])))
        title = response.xpath("//title/text()").extract_first()
        if title is None:
            return None
        title = quote(title.strip())
        qs.append("t_e={}".format(title))
        qs.append("t_d={}".format(quote(item["Twitter_Title"])))
        qs.append("t_t={}".format(title))
        qs.append("s_o=default")
        qs.append("l=en")
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
