# -*- coding: UTF-8 -*-

from mongoengine import Document, DictField, FloatField, ListField, StringField, IntField, DateTimeField, DecimalField


class Articles(Document):
    """
    Articles MongoDB Document model
    """
    # Meta
    Language = StringField()
    Type = StringField()
    Title = StringField()
    Description = StringField()
    URL = StringField(required=True, unique=True)
    Site_Name = StringField()
    Publisher = StringField()
    Author_FB = StringField()
    Tags = ListField(StringField())
    Section = StringField()
    Date_Published = DateTimeField()  # TODO
    Date_Modified = DateTimeField()  # TODO
    Headline_Image = StringField()
    Twitter_Description = StringField()
    Twitter_Title = StringField()
    Twitter_Site = StringField()
    Twitter_Image = StringField()
    Twitter_Creator = StringField()
    # Body
    Author = StringField()
    Author_Profile = StringField()
    Content_Body = StringField()
    Content_HTML = StringField()
    Total_Views = IntField()
    Comments = StringField()
    Shares = StringField()
    Comments = DictField()  # TODO
    Shares = DictField()  # TODO
    meta = {
        "strict": False,  # Ignore missing fields
        # "indexes": [
        #     {"fields": ("URL",), "unique": True}
        # ]
    }

    def __unicode__(self):
        return self.Title


class Market(Document):
    """
    Market MongoDB Document model
    """
    # Meta
    # Currency = StringField(required=True, unique=True)
    Currency = StringField(required=True)
    Market_Capitalization = DecimalField()
    Price = DecimalField()
    Volume = DecimalField()
    Change = DecimalField()
    Date_Published = DateTimeField()
    meta = {
        "strict": False,  # Ignore missing fields
    }

    def __unicode__(self):
        return self.Currency


class Twitter(Document):
    """
    Twitter Document model
    """
    # Meta
    Tweet_ID = IntField(required=True, unique=True)
    User = StringField(required=True)
    Tweet = StringField(required=True)
    Date_Published = DateTimeField()
    Longitude = FloatField()
    Latitude = FloatField()
    Country = StringField()
    Language = StringField()
    meta = {
        "strict": False,  # Ignore missing fields
    }

    def __unicode__(self):
        return self.User


class Gtrends(Document):
    """
    Google trends Document model
    """
    # Meta
    Keyword = StringField()
    Related_Queries = ListField(StringField())
    meta = {
        "strict": False,  # Ignore missing fields
    }

    def __unicode__(self):
        return self.Keyword
