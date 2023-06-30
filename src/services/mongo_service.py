from dataclasses import asdict
import hashlib
import os
from typing import Iterable
from bson import ObjectId

from dotenv import load_dotenv
from pymongo import MongoClient

from src.models.product import Product


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["prisfinder"]

finn_ads_collection = db["finn_ads"]
products_collection = db["products"]


def string_to_object_id(string: str) -> ObjectId:
    string_bytes = string.encode(encoding="utf8")
    hexdigest = hashlib.sha256(string_bytes).hexdigest()
    _id = ObjectId(hexdigest[:24])
    return _id


def _find_existing(product: Product):
    existing = products_collection.find_one(
        {
            "gtins": {
                "$in": product.gtins,
            },
        }
    )

    if existing:
        return Product.from_dict(existing)


def _update_product(existing: Product, new: Product):
    new_json = asdict(new)
    del new_json["_id"]
    products_collection.update_one(
        {"_id": existing._id},
        {"$set": new_json},
    )


def _create_product(product: Product):
    product_json = asdict(product)
    del product_json["_id"]
    products_collection.insert_one(product_json)


def upload_products(products: Iterable[Product]):
    for product in products:
        existing = _find_existing(product)

        if existing:
            return _update_product(existing, product)

        _create_product(product)
