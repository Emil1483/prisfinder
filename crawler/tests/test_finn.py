# python -m unittest tests.test_finn

import unittest

from src.models.product import Product, Retailer
from src.services.finn_service import FinnURLHandler
from src.services.web_page_service import WebPageService
from src.services.prisma_service import (
    clear_tables,
    fetch_finn_ads,
    upsert_product,
)


class TestDatabase(unittest.TestCase):
    def test_upsert_finn_ads(self):
        with WebPageService(FinnURLHandler()) as finn:
            finn.handle_url(self.product_id)

        finn_ads = fetch_finn_ads(self.product_id)

        self.assertGreater(len(finn_ads), 0)

    def test_unique_finn_ads(self):
        pass

    def setUp(self) -> None:
        clear_tables()

        self.product_id = upsert_product(
            Product(
                finn_query="Garmin Forerunner 245",
                name="GARMIN FORERUNNER 245 SPORTSKLOKKE SVART",
                description="Stilig smartklokke med GPS "
                "som motiverer deg til bedre trening og restitusjon",
                image="https://media.power-cdn.net/images/h-4877e411ac7093fd568b5a90f8deb153/products/1139441/1139441_11_600x600_t_g.webp",
                mpns=["010-02120-10"],
                gtins=["753759217174"],
                brand="Garmin",
                retailers=[
                    Retailer(
                        name="power",
                        price=2490,
                        sku="1139441",
                        url="https://www.power.no/mobil-og-foto/smartklokker-og-wearables/sportsklokke/garmin-forerunner-245-sportsklokke-svart/p-1139441/",
                        category="Mobil og foto/Smartklokker og "
                        "wearables/Sportsklokke",
                    )
                ],
            )
        )

    def tearDown(self) -> None:
        clear_tables()


if __name__ == "__main__":
    unittest.main()
