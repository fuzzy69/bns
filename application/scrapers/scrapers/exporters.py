# -*- coding: UTF-8 -*-

from scrapy.exporters import BaseItemExporter
from scrapy.utils.serialize import ScrapyJSONEncoder
from scrapy.utils.python import to_bytes


class CustomJsonItemExporter(BaseItemExporter):

    def __init__(self, file, **kwargs):
        self._configure(kwargs, dont_fail=True)
        self.file = file
        kwargs.setdefault("ensure_ascii", False)
        self.encoder = ScrapyJSONEncoder(**kwargs)
        self.first_item = True

    def start_exporting(self):
        self.file.write(b'')

    def finish_exporting(self):
        self.file.write(b'\n')

    def export_item(self, item):
        itemdict = dict(self._get_serialized_fields(item))
        bytes = to_bytes(self.encoder.encode(itemdict))
        self.file.write(bytes)
        self.file.write(b"\n")
