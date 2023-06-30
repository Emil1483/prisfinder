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
    sku: int
    url: str
    category: str


@dataclass_json
@dataclass(order=True, frozen=True)
class Product(object):
    name: str
    brand: str
    description: str
    image: str
    mpns: List[str]
    gtins: List[str]
    retailers: List[Retailer]
    category: Category | None = None
    _id: ObjectId | None = None
