import json
import requests

from src.services.prisma_service import (
    get_product_by_id,
    upsert_finn_ads,
)
from src.models.finn_ad import FinnAd, RawFinnAd
from src.services.url_handler import URLHandler
from src.models.product import Product


class NoFinnAds(Exception):
    pass


def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)


class FinnURLHandler(URLHandler):
    def handle_url(self, url: str) -> list[str]:
        if not url:
            return []

        product_id = int(url)
        product = get_product_by_id(product_id)

        raw_finn_ads = self.fetch_finn_ads(product)

        if not raw_finn_ads:
            raise NoFinnAds()

        finn_ads = [FinnAd.from_raw(ad, product_id) for ad in raw_finn_ads]
        upsert_finn_ads(finn_ads)
        return []

    def setup(self):
        pass

    def teardown(self):
        pass

    def fetch_finn_ads(self, product: Product) -> list[RawFinnAd]:
        assert product.finn_query

        query = product.finn_query.replace(" ", "+")

        def gen():
            match_count = None
            yielded_count = 0
            page = 0

            while match_count is None or yielded_count < match_count:
                page += 1

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
