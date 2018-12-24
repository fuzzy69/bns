# -*- coding: UTF-8 -*-

from application.scrapers.scrapers.spiders.ambcrypto import AmbcryptoSpider
from application.scrapers.scrapers.spiders.bitcoin import BitcoinSpider
from application.scrapers.scrapers.spiders.bitcoinist import BitcoinistSpider
from application.scrapers.scrapers.spiders.btcmanager import BtcmanagerSpider
from application.scrapers.scrapers.spiders.coindoo import CoindooSpider
from application.scrapers.scrapers.spiders.coinmarketcap import CoinmarketcapSpider
from application.scrapers.scrapers.spiders.coinspeaker import CoinspeakerSpider
from application.scrapers.scrapers.spiders.cryptoninjas import CryptoninjasSpider
from application.scrapers.scrapers.spiders.cryptovest import CryptovestSpider
from application.scrapers.scrapers.spiders.investinblockchain import InvestinblockchainSpider
from application.scrapers.scrapers.spiders.newsbtc import NewsbtcSpider
from application.scrapers.scrapers.spiders.ripple import RippleSpider
from application.scrapers.scrapers.spiders.twitter import TwitterSpider
from application.scrapers.scrapers.spiders.gtrends import GtrendsSpider

from application.scrapers.scrapers.spiders.testspider import TestSpider


SPIDERS = (
    AmbcryptoSpider,
    BitcoinSpider,
    BitcoinistSpider,
    BtcmanagerSpider,
    CoindooSpider,
    CoinmarketcapSpider,
    CoinspeakerSpider,
    CryptoninjasSpider,
    CryptovestSpider,
    InvestinblockchainSpider,
    NewsbtcSpider,
    RippleSpider,
    TwitterSpider,
    GtrendsSpider,

    # TestSpider,
)
