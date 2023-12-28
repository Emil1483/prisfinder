# python -m unittest tests.test_database

import unittest
import os

os.environ[
    "POSTGRESQL_URL"
] = "postgresql://test:rootpassword@localhost:5433/prisfinder"

os.environ["REDIS_URL"] = "redis://localhost:6379"

from src.services.prisma_service import (
    AmbiguousProductMatch,
    IdentifierChangeError,
    clear_tables,
    count_products,
    find_existing_product,
    get_ambiguous_products,
    get_product_by_id,
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

    def test_insert(self):
        mock_product = build_product(
            retailer="some retailer",
            sku="p-0",
            gtin="800",
            mpn="MP-0",
        )

        inserted_id = insert_product(mock_product)

        found_product = get_product_by_id(inserted_id)
        found_product.id = None

        self.assertEqual(mock_product, found_product)
        self.assertEqual(count_products(), 4)

    def test_upsert_existing_retailer(self):
        upserted_id = upsert_product(self.product_0)
        found_product = get_product_by_id(upserted_id)

        self.assertEqual(self.product_0, found_product)
        self.assertEqual(count_products(), 3)

    def test_upsert_new_retailer(self):
        upserted_id = upsert_product(
            build_product(gtin="700", mpn="M-3", retailer="eplehuset", sku="p-0")
        )

        found_product = get_product_by_id(upserted_id)

        self.assertListEqual(found_product.gtins, ["700"])
        self.assertListEqual(found_product.mpns, ["M-1", "M-3"])
        self.assertListEqual(
            [r.name for r in found_product.retailers],
            ["elkjop", "eplehuset"],
        )

        self.assertEqual(count_products(), 3)

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
            ["702", "M-1", "eplehuset", "p-0", AmbiguousProductMatch(self.id_0)],
            ["702", "M-2", "eplehuset", "p-0", AmbiguousProductMatch(self.id_2)],
            ["702", "M-3", "eplehuset", "p-0", None],
            ["702", None, "eplehuset", "p-0", None],
            [None, "M-1", "eplehuset", "p-0", AmbiguousProductMatch(self.id_0)],
            [None, "M-2", "eplehuset", "p-0", AmbiguousProductMatch(self.id_2)],
            [None, "M-3", "eplehuset", "p-0", None],
            [None, None, "eplehuset", "p-0", AssertionError()],
            ["700", "M-1", "elkjop", "p-0", self.id_0],
            ["700", "M-2", "elkjop", "p-0", IdentifierChangeError()],
            ["700", "M-3", "elkjop", "p-0", IdentifierChangeError()],
            ["700", None, "elkjop", "p-0", IdentifierChangeError()],
            ["701", "M-1", "elkjop", "p-0", IdentifierChangeError()],
            ["701", "M-2", "elkjop", "p-0", IdentifierChangeError()],
            ["701", "M-3", "elkjop", "p-0", IdentifierChangeError()],
            ["701", None, "elkjop", "p-0", IdentifierChangeError()],
            ["702", "M-1", "elkjop", "p-0", IdentifierChangeError()],
            ["702", "M-2", "elkjop", "p-0", IdentifierChangeError()],
            ["702", "M-3", "elkjop", "p-0", IdentifierChangeError()],
            ["702", None, "elkjop", "p-0", IdentifierChangeError()],
            [None, "M-1", "elkjop", "p-0", IdentifierChangeError()],
            [None, "M-2", "elkjop", "p-0", IdentifierChangeError()],
            [None, "M-3", "elkjop", "p-0", IdentifierChangeError()],
            [None, None, "elkjop", "p-0", AssertionError()],
        ]

        def extract_name(product_id: int):
            products = [self.product_0, self.product_1, self.product_2]
            if product_id is None:
                return None
            return next(p for p in products if p.id == product_id).name

        for gtin, mpn, retailer, sku, result in truth_table:
            if isinstance(result, Exception):
                try:
                    find_existing_product(
                        retailer_name=retailer,
                        sku=sku,
                        gtin=gtin,
                        mpn=mpn,
                    )

                except AmbiguousProductMatch as e:
                    assert isinstance(result, AmbiguousProductMatch)
                    expected_name = extract_name(result.conflicting_product_id)
                    yielded_name = extract_name(e.conflicting_product_id)

                    self.assertEqual(
                        e,
                        result,
                        f"Expected {expected_name} but got {yielded_name}"
                        f"on inputs {gtin=}, {mpn=} did not yield {result}",
                    )
                    continue

                except Exception as e:
                    self.assertEqual(
                        type(e),
                        type(result),
                        f"Expected {result=} to be raised, but "
                        f"{e=} was raised instead",
                    )
                    continue

                self.fail(f"inputs {gtin=}, {mpn=} did not yield {result=}")

            else:
                existing_product = find_existing_product(
                    retailer_name=retailer,
                    sku=sku,
                    gtin=gtin,
                    mpn=mpn,
                )
                existing_name = existing_product.name if existing_product else None
                expected_name = extract_name(result)
                self.assertEqual(
                    existing_product.id if existing_product else None,
                    result,
                    f'found "{existing_name}" but expected "{expected_name}" on input {gtin=}, {mpn=}',
                )

    def test_upsert_ambiguous_products(self):
        product0_to_upsert = build_product(
            retailer="eplehuset",
            sku="p-0",
            gtin="702",
            mpn="M-1",
        )
        product0_to_upsert.id = upsert_product(product0_to_upsert)

        self.assertEqual(count_products(), 4)

        root, children = get_ambiguous_products(product0_to_upsert.id)
        self.assertEqual(root, self.product_0)
        self.assertListEqual(children, [product0_to_upsert])

        product1_to_upsert = build_product(
            retailer="tings",
            sku="p-0",
            gtin="703",
            mpn="M-1",
        )
        product1_to_upsert.id = upsert_product(product1_to_upsert)

        self.assertEqual(count_products(), 5)

        root, children = get_ambiguous_products(product1_to_upsert.id)
        self.assertEqual(root, self.product_0)
        self.assertListEqual(children, [product0_to_upsert, product1_to_upsert])

        root, children = get_ambiguous_products(self.product_0.id)
        self.assertEqual(root, self.product_0)
        self.assertListEqual(children, [product0_to_upsert, product1_to_upsert])

    def tearDown(self) -> None:
        clear_tables()
