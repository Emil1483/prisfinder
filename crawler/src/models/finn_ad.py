# Generated by https://quicktype.io

from dataclasses import dataclass
from enum import Enum
from typing import List, Any
from bson import ObjectId

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass(order=True, frozen=True)
class Coordinates(object):
    lat: float
    lon: float


@dataclass_json
@dataclass(order=True, frozen=True)
class Image(object):
    url: str
    path: str
    height: int
    width: int
    aspect_ratio: float


@dataclass_json
@dataclass(order=True, frozen=True)
class Label(object):
    id: str
    text: str
    type: str


@dataclass_json
@dataclass(order=True, frozen=True)
class Price(object):
    amount: int
    currency_code: str


@dataclass_json
@dataclass(order=True, frozen=True)
class RawFinnAd(object):
    type: str
    id: str
    main_search_key: str
    heading: str
    location: str
    flags: List[str]
    timestamp: int
    coordinates: Coordinates
    ad_type: int
    labels: List[Label]
    extras: List[Any]
    price: Price
    distance: int
    trade_type: str
    image_urls: List[str]
    ad_id: int
    image: Image | None = None


@dataclass_json
@dataclass(order=True)
class FinnAd(object):
    id: int
    lat: float
    lng: float
    price: float
    timestamp: int
    title: str
    product_id: int
    image: str | None
    relevance: float | None = None

    @classmethod
    def from_raw(cls, ad: RawFinnAd, product_id: int):
        return FinnAd(
            id=ad.ad_id,
            lat=ad.coordinates.lat,
            lng=ad.coordinates.lon,
            price=ad.price.amount,
            product_id=product_id,
            timestamp=ad.timestamp,
            title=ad.heading,
            image=ad.image.url if ad.image else None,
        )
