from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass(order=True, frozen=True)
class URLValue(object):
    url: str
    next: str
    prev: str
    scrapet_at: int | None = None

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

    def copy_with(
        self,
        key: URLKey | None = None,
        value: URLValue | None = None,
    ):
        return URL(
            key=key or self.key,
            value=value or self.value,
        )
