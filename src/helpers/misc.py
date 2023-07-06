from datetime import datetime
import hashlib
from html.parser import HTMLParser

from bson import ObjectId


def hash_string(string: str, length=32):
    string_bytes = string.encode(encoding="utf8")
    hexdigest = hashlib.sha256(string_bytes).hexdigest()
    return hexdigest[:length]


def string_to_object_id(string: str) -> ObjectId:
    return ObjectId(hash_string(string, length=24))


def timestamp():
    return round(datetime.now().timestamp() * 1000)


class HTMLFilter(HTMLParser):
    text = ""

    def handle_data(self, data):
        self.text += data


def html_to_plaintext(html: str) -> str:
    html_filter = HTMLFilter()
    html_filter.feed(html)
    return html_filter.text
