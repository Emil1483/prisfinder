from dataclasses import dataclass
from dataclasses_json import dataclass_json
from types import NoneType

from src.helpers.misc import hash_string


@dataclass_json
@dataclass(order=True)
class URLValue(object):
    url: str
    next: str
    scraped_at: int | None = None
    failed_at: int | None = None

    def __post_init__(self):
        assert isinstance(self.url, str)
        assert isinstance(self.next, str)
        assert isinstance(self.scraped_at, (int, NoneType))
        assert isinstance(self.failed_at, (int, NoneType))


@dataclass(order=True, frozen=True)
class URLKey(object):
    domain: str
    id: str

    def __post_init__(self):
        assert isinstance(self.domain, str)
        assert isinstance(self.id, str)

    def __str__(self) -> str:
        return f"url:{self.domain}:{self.id}"


@dataclass(order=True, frozen=True)
class FailedURLKey(object):
    domain: str
    id: str

    @classmethod
    def from_url_key(cls, key: URLKey):
        return FailedURLKey(
            domain=key.domain,
            id=key.id,
        )

    def __post_init__(self):
        assert isinstance(self.domain, str)
        assert isinstance(self.id, str)

    def __str__(self) -> str:
        return f"failed_url:{self.domain}:{self.id}"


@dataclass(order=True, frozen=True)
class URL(object):
    value: URLValue
    key: URLKey

    def __post_init__(self):
        assert isinstance(self.value, URLValue)
        assert isinstance(self.key, URLKey)

    @property
    def visited(self):
        return self.value.scraped_at or self.value.failed_at

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
        return self.value.url
