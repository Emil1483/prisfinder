from pprint import pprint
import json
import requests
import numpy as np
import tensorflow_hub as hub


from src.models.finn_ad import FinnAd
from src.models.product import Category, Product
from src.services.mongo_service import fetch_product, update_product, upsert_finn_ads
from src.services.translator_service import translate_to_eng


class NoFinnAds(Exception):
    pass


def simularity(word1, word2):
    features = encoder([word1, word2])
    inner = np.inner(features, features)
    return inner[1][0]


def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)


finn_categories = load_json("finn_categories.json")
encoder = hub.load("./model")


def get_finn_category_parent(category: dict) -> dict:
    if category["parent"] is None:
        return None
    return next(c for c in finn_categories if c["id"] == category["parent"])


def get_finn_category_parents(category: dict) -> list[dict]:
    parent = get_finn_category_parent(category)
    if not parent:
        return []

    return [parent, *get_finn_category_parents(parent)]


def most_fitting_finn_category(name: str, predicted_depth: int) -> dict:
    best_score = 0
    best_finn_category = None
    for finn_category in finn_categories:
        parents = get_finn_category_parents(finn_category)
        actual_depth = len(parents)

        finn_name = finn_category["name_eng"]
        score = simularity(name, finn_name) / (
            1.4 ** abs(actual_depth - predicted_depth)
        )

        if score > best_score:
            best_score = score
            best_finn_category = finn_category

    return best_finn_category


def category_list_to_finn_category(category_list: list[str]) -> dict:
    def candidates():
        for i, name in enumerate(category_list):
            predicted_depth = i * 2 / (len(category_list) - 1)
            yield most_fitting_finn_category(name, predicted_depth)

    best_score = 0
    best_candidate = None

    for i, candidate in enumerate(candidates()):
        predicted_depth = i * 2 / (len(category_list) - 1)
        actual_depth = int(candidate["depth"])

        score = simularity(candidate["name_eng"], category_list[i])
        score *= 2 * (actual_depth + 1)
        score /= 1.2 ** abs(predicted_depth - actual_depth)

        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate


def parse_category(category_str: str) -> Category:
    category_list = [translate_to_eng(c) for c in category_str.split("/")]
    finn_category = category_list_to_finn_category(category_list)
    parents = get_finn_category_parents(finn_category)
    full_category = [*parents[::-1], finn_category]
    category_ids = [c["id"] for c in full_category]
    category_ids.extend([None] * (3 - len(full_category)))
    return Category(
        main=int(category_ids[0]),
        sub=int(category_ids[1]),
        product=int(category_ids[2]),
    )


def fetch_finn_ads(product: Product) -> list[FinnAd]:
    def gen_category_ids():
        if product.category.main:
            yield str(product.category.main)

        if product.category.sub:
            yield str(product.category.sub)

        if product.category.product:
            yield str(product.category.product)

    category_ids = [*gen_category_ids()]
    n = len(category_ids)

    prefix = ["category", "sub_category", "product_category"][n - 1]
    category_param = f"{prefix}={n-1}.{'.'.join(category_ids)}"

    query = product.name.replace(" ", "+")

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

    return [
        FinnAd.from_finn_dict(ad, product._id)
        for ad in gen()
        if ad["trade_type"] == "Til salgs"
    ]


def populate_product(product_id: str):
    product = fetch_product(product_id)

    if product.category is None:
        category = parse_category(product.retailers[0].category)
        product = product.copy_with_category(category)
        update_product(product, product)

    finn_ads = fetch_finn_ads(product)

    if not finn_ads:
        raise NoFinnAds()

    upsert_finn_ads(finn_ads)
    return finn_ads


if __name__ == "__main__":
    # pprint(populate_product("64a534654d1aba67b4243eaf")) SANITIZED PRODUCT NAME
    # pprint(populate_product("64a5509b2721b2407a0028bd")) SANITIZED PRODUCT NAME
    # pprint(populate_product("64a550d868b8fc7f7f62e645")) ALREADY SANITIZED
    pprint(populate_product("64a551512a9c612eb7e3227e"))  # SANITATION NEEDED
