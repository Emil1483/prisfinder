from dataclasses import asdict
import os
from typing import Any, Generator, Iterable
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import DeleteOne, MongoClient, UpdateOne

from src.helpers.misc import string_to_object_id
from src.models.finn_ad import FinnAd
from src.models.product import Product


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["prisfinder"]

finn_ads_collection = db["finn_ads"]
products_collection = db["products"]
urls_collection = db["urls"]


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


def update_product(existing: Product, new: Product):
    new_json = asdict(new)
    del new_json["_id"]

    # TODO: merge data

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
            return update_product(existing, product)

        _create_product(product)


def upsert_finn_ads(finn_ads: list[FinnAd]):
    def gen():
        for ad in finn_ads:
            _id = string_to_object_id(str(ad.ad_id))
            yield UpdateOne(
                {"_id": _id},
                {
                    "$set": {
                        "_id": _id,
                        **ad.to_dict(),
                    },
                },
                upsert=True,
            )

    operations = [*gen()]

    return finn_ads_collection.bulk_write(operations)


def fetch_product(product_id: str) -> Product:
    product_dict = products_collection.find_one({"_id": ObjectId(product_id)})
    return Product.from_dict(product_dict)


def fetch_products(limit=10) -> Generator[Product, Any, None]:
    for doc in products_collection.find({})[:limit]:
        yield Product.from_dict(doc)


def fetch_pending_urls(domain: str, limit=10) -> list[str]:
    def gen():
        for doc in urls_collection.find({"domain": domain})[:limit]:
            yield doc["url"], DeleteOne({"_id": doc["_id"]})

    result = [*gen()]

    if not result:
        return []

    urls, operations = zip(*result)

    # urls_collection.bulk_write(list(operations))

    return urls


def insert_pending_urls(domain: str, urls: Iterable[str]):
    def gen():
        for url in urls:
            yield {
                "_id": string_to_object_id(url),
                "domain": domain,
                "url": url,
            }

    docs = [*gen()]
    return urls_collection.insert_many(docs)
