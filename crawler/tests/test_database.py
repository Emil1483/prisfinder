# python -m unittest tests.test_database

import unittest
import pytest

from src.services.prisma_service import (
    AmbiguousProductMatch,
    clear_tables,
    find_existing_product,
    insert_product,
    upsert_product,
)
from src.models.product import Product, Retailer


def build_product(retailer: str, gtin: str = None, mpn: str = None, sku: str = None):
    return Product(
        name=f"name {gtin=} {mpn=} {sku=}",
        description="description",
        brand="brand",
        gtins=[gtin] if gtin else [],
        mpns=[mpn] if mpn else [],
        image="image.jpg",
        retailers=[
            Retailer(
                category="general",
                name=retailer,
                price=399.99,
                url="https://www.example.com",
                sku=sku,
            ),
        ],
    )


class TestDatabase(unittest.TestCase):
    def test_insert(self):
        clear_tables()

        mock_product = build_product(
            retailer="some retailer",
            sku="p-0",
            gtin="800",
            mpn="MP-0",
        )

        insert_product(mock_product)

        found_product = find_existing_product(
            gtin="800",
            retailer_name="some retailer",
            sku="p-0",
        )
        found_product.id = None

        self.assertEqual(mock_product, found_product)

    def test_upsert_existing_retailer(self):
        pass

    def test_upsert_new_retailer(self):
        pass

    def test_find_existing_product(self):
        truth_table = [
            ["700", "M-1", "eplehuset", "p-0", self.id_0],
            ["700", "M-2", "eplehuset", "p-0", self.id_0],
            ["700", "M-3", "eplehuset", "p-0", self.id_0],
            ["700", None, "eplehuset", "p-0", self.id_0],
            ["701", "M-1", "eplehuset", "p-0", self.id_1],
            ["701", "M-2", "eplehuset", "p-0", self.id_1],
            ["701", "M-3", "eplehuset", "p-0", self.id_1],
            ["701", None, "eplehuset", "p-0", self.id_1],
            ["702", "M-1", "eplehuset", "p-0", AmbiguousProductMatch],
            ["702", "M-2", "eplehuset", "p-0", AmbiguousProductMatch],
            ["702", "M-3", "eplehuset", "p-0", None],
            ["702", None, "eplehuset", "p-0", None],
            [None, "M-1", "eplehuset", "p-0", AmbiguousProductMatch],
            [None, "M-2", "eplehuset", "p-0", AmbiguousProductMatch],
            [None, "M-3", "eplehuset", "p-0", None],
            [None, None, "eplehuset", "p-0", AssertionError],
        ]

        for gtin, mpn, retailer, sku, result in truth_table:
            if isinstance(result, type):
                self.assertRaises(
                    result,
                    find_existing_product,
                    retailer_name=retailer,
                    sku=sku,
                    gtin=gtin,
                    mpn=mpn,
                )
            else:
                existing_product = find_existing_product(
                    retailer_name=retailer,
                    sku=sku,
                    gtin=gtin,
                    mpn=mpn,
                )
                products = [self.product_0, self.product_1, self.product_2]
                expected_product = (
                    next(p for p in products if p.id == result) if result else None
                )
                existing_name = existing_product.name if existing_product else None
                expected_name = expected_product.name if existing_product else None
                self.assertEqual(
                    existing_product.id if existing_product else None,
                    result,
                    f'found "{existing_name}" but expected "{expected_name}" on input {gtin=}, {mpn=}',
                )

    def test_unique_finn_ads(self):
        pass

    def setUp(self) -> None:
        clear_tables()

        self.product_0 = build_product(
            gtin="700", mpn="M-1", retailer="elkjop", sku="p-0"
        )
        self.product_1 = build_product(
            gtin="701", mpn=None, retailer="komplett", sku="p-0"
        )
        self.product_2 = build_product(
            gtin=None, mpn="M-2", retailer="power", sku="p-0"
        )

        self.product_0.id = insert_product(self.product_0)
        self.product_1.id = insert_product(self.product_1)
        self.product_2.id = insert_product(self.product_2)

        self.id_0 = self.product_0.id
        self.id_1 = self.product_1.id
        self.id_2 = self.product_2.id

    def tearDown(self) -> None:
        clear_tables()
