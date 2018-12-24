# -*- coding: UTF-8 -*-

from sqlalchemy import Column, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime, Integer, String
from sqlalchemy.dialects.mysql import INTEGER

from application.misc import ScrapeType, SpiderStatus, OK


Base = declarative_base()


class BaseTable(Base):
    """

    """
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    # date_created = Column(DateTime, default=func.current_timestamp())
    # date_modified = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())


class Jobs(BaseTable):
    """

    """
    __tablename__ = "jobs"

    task_id = Column(String(100))
    spider_name = Column(String(100), nullable=False, index=True)
    spider_status = Column(INTEGER, nullable=False, default=SpiderStatus.PENDING)
    scrape_type = Column(INTEGER, nullable=False, default=ScrapeType.ALL)
    use_proxies = Column(INTEGER, nullable=False, default=OK.NO)
    file = Column(INTEGER, nullable=False, default=OK.NO)
    db = Column(INTEGER, nullable=False, default=OK.NO)
    images = Column(INTEGER, nullable=False, default=OK.NO)
    items_scraped = Column(INTEGER, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    # log_file = Column(String(100))


class PeriodicJobs(BaseTable):
    """

    """
    __tablename__ = "periodic_jobs"

    spider_name = Column(String(100), nullable=False, index=True, unique=True)
    scrape_type = Column(INTEGER, nullable=False, default=ScrapeType.ALL)
    use_proxies = Column(INTEGER, nullable=False, default=OK.NO)
    file = Column(INTEGER, nullable=False, default=OK.NO)
    db = Column(INTEGER, nullable=False, default=OK.NO)
    images = Column(INTEGER, nullable=False, default=OK.NO)
    repeat_time = Column(INTEGER, nullable=False, default=0)
    enabled = Column(INTEGER, nullable=False, default=OK.NO)


# class Settings(Base):
#     """
#
#     """
#     __tablename__ = "settings"
#
#     id = Column(Integer, primary_key=True)
#     delay = Column(INTEGER, nullable=False, default=3)
#     timeout = Column(INTEGER, nullable=False, default=20)
#     retries = Column(INTEGER, nullable=False, default=2)
#     scrape_type = Column(INTEGER, nullable=False, default=ScrapeType.ALL)
#     use_proxies = Column(INTEGER, nullable=False, default=OK.NO)
#     file = Column(INTEGER, nullable=False, default=OK.NO)
#     db = Column(INTEGER, nullable=False, default=OK.NO)
#     images = Column(INTEGER, nullable=False, default=OK.NO)
#     mongo_uri = Column(String(100), nullable=False, default="mongodb://10.0.3.92:27017")
#     mongo_db = Column(String(100), nullable=False, default="bitcoin_news")


def init_db(db_uri):
    engine = create_engine(db_uri)
    # DBSession = sessionmaker(bind=engine)
    # db_session = DBSession()
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    # from config import WEBUI_DATABASE_URI
    #
    # engine = create_engine(WEBUI_DATABASE_URI)
    # DBSession = sessionmaker(bind=engine)
    # db_session = DBSession()
    #
    # Base.metadata.create_all(engine)
    #
    # settings = Settings()
    # db_session.add(settings)
    # db_session.commit()
    pass
