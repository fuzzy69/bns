# -*- coding: utf-8 -*-

from scrapy import Field, Item


class ArticleItem(Item):
    """
    Scrapy item class scraped news articles
    """
    # Meta
    Language = Field()
    Type = Field()
    Title = Field()
    Description = Field()
    URL = Field()
    Site_Name = Field()
    Publisher = Field()
    Author_FB = Field()
    Tags = Field()
    Section = Field()
    Date_Published = Field()
    Date_Modified = Field()
    Headline_Image = Field()
    Twitter_Description = Field()
    Twitter_Title = Field()
    Twitter_Site = Field()
    Twitter_Image = Field()
    Twitter_Creator = Field()
    # Body
    Author = Field()
    Author_Profile = Field()
    Content_Body = Field()
    Content_HTML = Field()
    Total_Views = Field()
    Comments = Field()  # TODO {user: comment, user: comment}
    Shares = Field()  # TODO {twitter: count, facebook: count, google:count, linkedin count, reddit: count,


class MarketItem(Item):
    """
    """
    Currency = Field()
    Market_Capitalization = Field()
    Price = Field()
    Volume = Field()
    Change = Field()
    Date_Published = Field()


class TwitterItem(Item):
    """
    """
    Tweet_ID = Field()
    User = Field()
    Tweet = Field()
    Date_Published = Field()
    Longitude = Field()
    Latitude = Field()
    Country = Field()
    Language = Field()


class GtrendsItem(Item):
    """
    """
    Keyword = Field()
    Related_Queries = Field()


class TestItem(Item):
    """
    """
    URL = Field()
    title = Field()
    content = Field()
