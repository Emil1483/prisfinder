from dataclasses import dataclass
from types import NoneType
from typing import List

from dataclasses_json import dataclass_json

from src.models.finn_ad import FinnAd


@dataclass_json
@dataclass(order=True, frozen=True)
class Category(object):
    main: int
    sub: int
    product: int


@dataclass_json
@dataclass(order=True, frozen=True)
class Retailer(object):
    name: str
    price: float
    sku: str
    url: str
    category: str

    @property
    def id(self):
        return f"{self.name}_{self.sku}"


# TODO: use pydantic
@dataclass_json
@dataclass(order=True)
class Product(object):
    name: str
    description: str
    image: str
    mpns: List[str]
    gtins: List[str]
    retailers: List[Retailer]
    finn_ads: List[FinnAd] = None
    brand: str = None
    category: Category | None = None
    finn_query: str | None = None
    id: int | None = None

    def __post_init__(self):
        if not self.finn_ads:
            self.finn_ads = []

        assert all(isinstance(mpn, str) for mpn in self.mpns)
        assert all(isinstance(gtin, str) for gtin in self.gtins)
        assert all(isinstance(retailer, Retailer) for retailer in self.retailers)
        assert all(isinstance(finn_ad, FinnAd) for finn_ad in self.finn_ads)
        assert isinstance(self.name, str)
        assert isinstance(self.description, str)
        assert isinstance(self.image, str)
        assert isinstance(self.brand, (NoneType, str))
        assert isinstance(self.category, (NoneType, Category))
        assert isinstance(self.finn_query, (NoneType, str))
        assert isinstance(self.id, (NoneType, int))
