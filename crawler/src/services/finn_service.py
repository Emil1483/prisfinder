import json
import requests
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from src.services.prisma_service import (
    get_product_by_id,
    update_product,
    upsert_finn_ads,
)
from src.models.finn_ad import FinnAd, RawFinnAd
from src.services.url_handler import URLHandler
from src.models.product import Category, Product
from src.services.translator_service import translate_to_eng


class NoFinnAds(Exception):
    pass


def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)


class FinnURLHandler(URLHandler):
    def handle_url(self, url: str) -> list[str]:
        product_id = int(url)
        product = get_product_by_id(product_id)

        if product.category is None:
            product.category = self.parse_category(product.retailers[0].category)
            update_product(product_id, product)

        raw_finn_ads = self.fetch_finn_ads(product)

        if not raw_finn_ads:
            raise NoFinnAds()

        finn_ads = [FinnAd.from_raw(ad, product_id) for ad in raw_finn_ads]
        upsert_finn_ads(finn_ads)
        return []

    def setup(self):
        self.finn_categories = load_json("finn_categories.json")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def teardown(self):
        pass

    def simularity(self, word1, word2):
        return cos_sim(self.model.encode(word1), self.model.encode(word2))

    def get_finn_category_parent(self, category: dict) -> dict:
        if category["parent"] is None:
            return None
        return next(c for c in self.finn_categories if c["id"] == category["parent"])

    def get_finn_category_parents(self, category: dict) -> list[dict]:
        parent = self.get_finn_category_parent(category)
        if not parent:
            return []

        return [parent, *self.get_finn_category_parents(parent)]

    def most_fitting_finn_category(self, name: str, predicted_depth: int) -> dict:
        best_score = 0
        best_finn_category = None
        for finn_category in self.finn_categories:
            parents = self.get_finn_category_parents(finn_category)
            actual_depth = len(parents)

            finn_name = finn_category["name_eng"]
            score = self.simularity(name, finn_name) / (
                1.4 ** abs(actual_depth - predicted_depth)
            )

            if score > best_score:
                best_score = score
                best_finn_category = finn_category

        return best_finn_category

    def category_list_to_finn_category(self, category_list: list[str]) -> dict:
        def candidates():
            for i, name in enumerate(category_list):
                predicted_depth = i * 2 / (len(category_list) - 1)
                yield self.most_fitting_finn_category(name, predicted_depth)

        best_score = 0
        best_candidate = None

        for i, candidate in enumerate(candidates()):
            predicted_depth = i * 2 / (len(category_list) - 1)
            actual_depth = int(candidate["depth"])

            score = self.simularity(candidate["name_eng"], category_list[i])
            score *= 2 * (actual_depth + 1)
            score /= 1.2 ** abs(predicted_depth - actual_depth)

            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate

    def parse_category(self, category_str: str) -> Category:
        category_list = [translate_to_eng(c) for c in category_str.split("/")]
        finn_category = self.category_list_to_finn_category(category_list)
        parents = self.get_finn_category_parents(finn_category)
        full_category = [*parents[::-1], finn_category]
        category_ids = [int(c["id"]) for c in full_category]
        category_ids.extend([None] * (3 - len(full_category)))
        return Category(
            main=category_ids[0],
            sub=category_ids[1],
            product=category_ids[2],
        )

    def fetch_finn_ads(self, product: Product) -> list[RawFinnAd]:
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
        if product.finn_query:
            query = product.finn_query.replace(" ", "+")

        def gen():
            match_count = None
            yielded_count = 0
            page = 0

            while match_count is None or yielded_count < match_count:
                page += 1

                # TODO: fix categories
                # response = requests.get(
                #     f"https://www.finn.no/api/search-qf?searchkey=SEARCH_ID_BAP_COMMON&{category_param}&q={query}&sort=RELEVANCE&vertical=bap&page={page}",
                # )

                response = requests.get(
                    f"https://www.finn.no/api/search-qf?searchkey=SEARCH_ID_BAP_COMMON&q={query}&sort=RELEVANCE&vertical=bap&page={page}",
                )

                res_json = response.json()

                match_count = res_json["metadata"]["result_size"]["match_count"]

                ads = res_json["docs"]
                yielded_count += len(ads)
                for ad in ads:
                    yield ad

        return [
            RawFinnAd.from_dict(ad) for ad in gen() if ad["trade_type"] == "Til salgs"
        ]
