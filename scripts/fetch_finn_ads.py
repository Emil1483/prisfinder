import json
from pprint import pprint

import requests


def fetch_finn_ads(product: dict) -> list[dict]:
    category = product["category"]

    def gen_category_ids():
        if category["main"]:
            yield str(category["main"])

        if category["sub"]:
            yield str(category["sub"])

        if category["product"]:
            yield str(category["product"])

    category_ids = [*gen_category_ids()]
    n = len(category_ids)

    prefix = ["category", "sub_category", "product_category"][n - 1]
    category_param = f"{prefix}={n-1}.{'.'.join(category_ids)}"

    query = product["name"].replace(" ", "+")

    def gen():
        match_count = None
        yielded_count = 0
        page = 0

        while match_count is None or yielded_count < match_count:
            page += 1

            response = requests.get(
                f"https://www.finn.no/api/search-qf?searchkey=SEARCH_ID_BAP_COMMON&{category_param}&q={query}&sort=RELEVANCE&vertical=bap&page={page}",
            )

            res_json = response.json()

            match_count = res_json["metadata"]["result_size"]["match_count"]

            ads = res_json["docs"]
            yielded_count += len(ads)
            for ad in ads:
                yield ad

    return [ad for ad in gen() if ad["trade_type"] == "Til salgs"]


def load_json(file: str) -> dict:
    with open(file, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    test_products = load_json("test_products.json")
    for product in test_products:
        finn_ads = fetch_finn_ads(product)
        pprint(finn_ads)
