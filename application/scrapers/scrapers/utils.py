# -*- coding: UTF-8 -*-

import logging
import re
from time import strftime

from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging, _get_handler, TopLevelFormatter


def multi_replace(text, dic):
    """
    Replace multiple strings at once
    :param str text: target text for replacing
    :param dict dic: dictionary of replacement items in format search string as key and replacement string as value
    :return: new string with replaced matches
    """
    regex = re.compile('|'.join(map(re.escape, dic)))

    def matcher(match):
        return dic[match.group(0)]

    return regex.sub(matcher, text)


def cleanup_html(html):
    """
    Remove excess whitespace characters
    :param string html: input html code
    :return: cleaned up html code string
    """
    html = re.sub(r"[\r\n\t]*", '', html)  # remove escaped whitespace chars
    html = re.sub(r"\s+", ' ', html)  # trim more than one consecutive space

    return html


class CustomTopLevelFormatter(TopLevelFormatter):
    """
    Custom log file formatter to avoid mixing logs from multiple scrapers in the same log file
    """
    def __init__(self, loggers=None, name=None):
        super().__init__()
        self.loggers = loggers or []
        self.name = name

    def filter(self, record):
        if self.name in record.name:
            return False
        if hasattr(record, "spider"):
            if record.spider.name != self.name:
                return False
            record.name = record.spider.name + "." + record.name
        elif hasattr(record, "crawler") and hasattr(record.crawler, "spidercls"):
            if record.crawler.spidercls.name != self.name:
                return False
            record.name = record.crawler.spidercls.name + "." + record.name
        elif any(record.name.startswith(l + '.') for l in self.loggers):
            record.name = record.name.split('.', 1)[0]

        return True


def init_custom_log(name):
    """
    Apply custom log settings to spider, call it from the spider __init__ method
    :param str name: scrapy spider name
    :return: None
    """
    log_file = "/mnt/ramdisk/{} {}.log".format(name, strftime("%Y-%m-%d %H:%M:%S"))
    configure_logging(
        {"LOG_FILE": log_file},
        install_root_handler=False
    )
    settings = get_project_settings()
    settings["LOG_FILE"] = log_file
    settings["LOG_LEVEL"] = "INFO"
    settings["DISABLE_TOPLEVELFORMATTER"] = True
    handler = _get_handler(settings)
    handler.addFilter(CustomTopLevelFormatter(loggers=[__name__], name=name))
    logging.root.addHandler(handler)


def split_list(li, n):
    """Split list into n lists

    :param list li: list to split
    :param int n: split chunks count
    :return: list of n lists
    """
    k, m = divmod(len(li), n)

    return [li[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def string_to_float(string: str) -> float:
    """
    Converts text string to float number
    :param str string: number string
    :return: float number
    :raise: TypeError
    """
    string = re.sub(r"[^\d\.\-e]", '', string.strip())  # Remove excess characters
    number = float(string)  # Convert to float
    string = format(number, ".16f")  # Up to 10 decimals max

    return float(string)


if __name__ == "__main__":
    pass
