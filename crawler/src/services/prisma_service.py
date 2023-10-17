from prisma import Prisma
from src.models.product import Category, Product, Retailer

prisma = Prisma()

prisma.connect()


class AmbiguousProductMatch(Exception):
    pass


class IdentifierChangeError(Exception):
    pass


def insert_product(product: Product):
    result = prisma.product.create(
        data={
            "name": product.name,
            "description": product.description,
            "brand": product.brand,
            "finn_query": product.finn_query,
            "image": product.image,
            "category": product.category.to_json() if product.category else "null",
            "gtins": {
                "create": [{"gtin": gtin} for gtin in product.gtins],
            },
            "mpns": {
                "create": [{"mpn": mpn} for mpn in product.mpns],
            },
            "retailers": {
                "create": [
                    {
                        "name": retailer.name,
                        "price": retailer.price,
                        "sku": retailer.sku,
                        "url": retailer.url,
                        "category": retailer.category,
                    }
                    for retailer in product.retailers
                ],
            },
        },
    )

    return result.id


def find_existing_product(
    retailer_name: str,
    sku: str,
    gtin: str = None,
    mpn: str = None,
):
    assert retailer_name and sku
    assert gtin or mpn

    def gen():
        if gtin:
            yield {
                "gtins": {
                    "some": {
                        "gtin": gtin,
                    }
                }
            }

        if mpn:
            yield {
                "mpns": {
                    "some": {
                        "mpn": mpn,
                    }
                }
            }

        if retailer_name and sku:
            yield {
                "retailers": {
                    "some": {
                        "name": retailer_name,
                        "sku": sku,
                    }
                }
            }

    prisma_products = prisma.product.find_many(
        where={"OR": [*gen()]},
        include={
            "gtins": True,
            "mpns": True,
            "retailers": True,
        },
    )

    if not prisma_products:
        return None

    prisma_product = prisma_products[0]
    for product in prisma_products:
        if gtin in [g.gtin for g in product.gtins]:
            prisma_product = product
            break

    if gtin not in [gtin.gtin for gtin in prisma_product.gtins]:
        raise AmbiguousProductMatch()

    return Product(
        id=prisma_product.id,
        name=prisma_product.name,
        description=prisma_product.description,
        image=prisma_product.image,
        brand=prisma_product.brand,
        finn_query=prisma_product.finn_query,
        gtins=[gtin.gtin for gtin in prisma_product.gtins],
        mpns=[mpn.mpn for mpn in prisma_product.mpns],
        retailers=[
            Retailer(
                name=r.name,
                sku=r.sku,
                url=r.url,
                category=r.category,
                price=r.price,
            )
            for r in prisma_product.retailers
        ],
        category=Category(
            main=prisma_product["main"],
            product=prisma_product["product"],
            sub=prisma_product["sub"],
        )
        if prisma_product.category
        else None,
    )


def upsert_product(product: Product):
    if product.gtins:
        assert len(product.gtins) == 1

    if product.mpns:
        assert len(product.mpns) == 1

    if product.retailers:
        assert len(product.retailers) == 1

    gtin = product.gtins[0] if product.gtins else None
    mpn = product.mpns[0] if product.mpns else None
    retailer_name = product.retailers[0].name if product.retailers else None
    sku = product.retailers[0].sku if product.retailers else None

    existing = find_existing_product(
        gtin=gtin,
        mpn=mpn,
        retailer_name=retailer_name,
        sku=sku,
    )

    if not existing:
        insert_product(product)
        return

    existing_retailer_ids = [r.id for r in existing.retailers]
    retailers_to_add = [
        r for r in product.retailers if r.id not in existing_retailer_ids
    ]

    gtins_to_add = [gtin for gtin in product.gtins if gtin not in existing.gtins]

    mpns_to_add = [mpn for mpn in product.mpns if mpn not in existing.mpns]

    if retailers_to_add or gtins_to_add or mpns_to_add:
        prisma.product.update(
            where={"id": existing.id},
            data={
                "gtins": {
                    "create": [{"gtin": gtin} for gtin in gtins_to_add],
                },
                "mpns": {
                    "create": [{"mpn": mpn} for mpn in mpns_to_add],
                },
                "retailers": {
                    "create": [
                        {
                            "name": r.name,
                            "category": r.category,
                            "price": r.price,
                            "sku": r.sku,
                        }
                        for r in retailers_to_add
                    ],
                },
            },
        )


def clear_tables():
    prisma.product.delete_many()
