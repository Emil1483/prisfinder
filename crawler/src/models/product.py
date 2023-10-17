from dataclasses import dataclass
from typing import List
from bson import ObjectId

from dataclasses_json import dataclass_json


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


@dataclass_json
@dataclass(order=True)
class Product(object):
    name: str
    description: str
    image: str
    mpns: List[str]
    gtins: List[str]
    retailers: List[Retailer]
    brand: str = None
    category: Category | None = None
    finn_query: str | None = None
    id: str | None = None

    def __post_init__(self):
        assert all(isinstance(mpn, str) for mpn in self.mpns)
        assert all(isinstance(gtin, str) for gtin in self.gtins)
        assert all(isinstance(retailer, Retailer) for retailer in self.retailers)

    def copy_with_category(self, category: Category):
        return Product(
            name=self.name,
            brand=self.brand,
            description=self.description,
            image=self.image,
            mpns=self.mpns,
            gtins=self.gtins,
            retailers=self.retailers,
            category=category,
            finn_query=self.finn_query,
        )
