from dataclasses import dataclass
from types import NoneType
from enum import Enum
from urllib.parse import urlparse

from dataclasses_json import dataclass_json

from src.helpers.misc import hash_string


@dataclass_json
@dataclass(order=True)
class URLValue(object):
    url: str
    next: str
    scraped_at: int | None = None

    def __post_init__(self):
        assert isinstance(self.url, str)
        assert isinstance(self.next, str)
        assert isinstance(self.scraped_at, (int, NoneType))


@dataclass(order=True, frozen=True)
class URLKey(object):
    domain: str
    id: str

    def __post_init__(self):
        assert isinstance(self.domain, str)
        assert isinstance(self.id, str)

    def __str__(self) -> str:
        return f"url:{self.domain}:{self.id}"

    @classmethod
    def from_string(cls, string: str):
        _, domain, url_id = string.split(":")
        return URLKey(
            domain=domain,
            id=url_id,
        )


@dataclass(order=True, frozen=True)
class URL(object):
    value: URLValue
    key: URLKey

    def __post_init__(self):
        assert isinstance(self.value, URLValue)
        assert isinstance(self.key, URLKey)

    @classmethod
    def from_string(cls, url_str: str, domain: str):
        url_id = hash_string(url_str)
        return URL(
            key=URLKey(
                domain=domain,
                id=url_id,
            ),
            value=URLValue(
                url=url_str,
                next=url_id,
            ),
        )

    def __str__(self):
        scraped_at = self.value.scraped_at
        return f"{self.value.url} {scraped_at=}"
