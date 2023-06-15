from datetime import datetime
import hashlib


def hash_string(string: str, length=32):
    string_bytes = string.encode(encoding="utf8")
    hexdigest = hashlib.sha256(string_bytes).hexdigest()
    return hexdigest[:length]


def timestamp():
    return round(datetime.now().timestamp() * 1000)
