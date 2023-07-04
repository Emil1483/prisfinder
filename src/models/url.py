from dataclasses import dataclass
from types import NoneType
from enum import Enum
from urllib.parse import urlparse

from dataclasses_json import dataclass_json

from src.helpers.misc import hash_string


class URLStatus(Enum):
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass_json
@dataclass(order=True, frozen=True)
class URLValue(object):
    url: str
    next: str
    prev: str
    scrapet_at: int | None = None

    def __post_init__(self):
        assert isinstance(self.url, str)
        assert isinstance(self.next, str)
        assert isinstance(self.prev, str)
        assert isinstance(self.scrapet_at, (int, NoneType))

    def copy_with(
        self,
        scrapet_at: int | None = None,
        next_id: str | None = None,
        prev_id: str | None = None,
    ):
        return URLValue(
            scrapet_at=scrapet_at or self.scrapet_at,
            next=next_id or self.next,
            prev=prev_id or self.prev,
            url=self.url,
        )


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
    def from_url_string(cls, url_str: str):
        domain = urlparse(url_str).netloc.replace("www.", "")
        url_id = hash_string(url_str)
        return URL(
            key=URLKey(
                domain=domain,
                id=url_id,
            ),
            value=URLValue(
                url=url_str,
                next=url_id,
                prev=url_id,
            ),
        )

    def __str__(self):
        return self.value.url

    def copy_with(
        self,
        key: URLKey | None = None,
        value: URLValue | None = None,
    ):
        return URL(
            key=key or self.key,
            value=value or self.value,
        )
