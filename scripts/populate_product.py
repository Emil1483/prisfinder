import hashlib
import os

from bson import ObjectId
from load_dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

from fetch_finn_ads import fetch_finn_ads

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


def upsert_finn_ads(finn_ads: list[dict]):
    def gen():
        for ad in finn_ads:
            _id = string_to_object_id(str(ad["ad_id"]))
            yield UpdateOne(
                {"_id": _id},
                {
                    "$set": {
                        "_id": _id,
                        **ad,
                    },
                },
                upsert=True,
            )

    operations = [*gen()]

    write_result = finn_ads_collection.bulk_write(operations)

    print(
        f"added finn ads: upserted:{write_result.upserted_count} modified:{write_result.modified_count} matched:{write_result.matched_count} inserted:{write_result.inserted_count}"
    )


def populate_product(product_id: str):
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    finn_ads = fetch_finn_ads(product)
    upsert_finn_ads(finn_ads)


if __name__ == "__main__":
    populate_product("64831dcf822c50174f331e15")
