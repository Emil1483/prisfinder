from dataclasses import asdict, dataclass
from math import floor
from random import random
from typing import Iterable
from prisma import Prisma
from src.models.finn_ad import FinnAd
from src.models.product import Category, Product, Retailer
from prisma.models import Product as PrismaProduct

prisma = Prisma()

prisma.connect()


@dataclass
class AmbiguousProductMatch(Exception):
    conflicting_product_id: int


class IdentifierChangeError(Exception):
    pass


def fetch_products_sample(sample_size: int):
    count = prisma.product.count()
    skip = floor(random() * (count - sample_size))
    prisma_products = prisma.product.find_many(
        take=sample_size,
        skip=skip,
        include={
            "gtins": True,
            "mpns": True,
            "retailers": True,
            "finn_ads": True,
        },
    )

    return [as_product_model(p) for p in prisma_products]


def insert_product(product: Product, ambiguous_to_id: int | None = None):
    result = prisma.product.create(
        data={
            "name": product.name,
            "description": product.description,
            "brand": product.brand,
            "finn_query": product.finn_query,
            "image": product.image,
            "category": product.category.to_json() if product.category else "null",
            "ambiguous_to_id": ambiguous_to_id,
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


def as_product_model(prisma_product: PrismaProduct):
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
            main=prisma_product.category["main"],
            product=prisma_product.category["product"],
            sub=prisma_product.category["sub"],
        )
        if prisma_product.category
        else None,
        finn_ads=[
            FinnAd(
                id=ad.id,
                image=ad.image,
                lat=ad.lat,
                lng=ad.lng,
                price=ad.price,
                timestamp=ad.timestamp,
                title=ad.title,
                product_id=ad.product_id,
                relevance=ad.relevance,
            )
            for ad in prisma_product.finn_ads
        ]
        if prisma_product.finn_ads
        else [],
    )


def get_product_by_id(id: int):
    prisma_product = prisma.product.find_unique(
        where={"id": id},
        include={
            "gtins": True,
            "mpns": True,
            "retailers": True,
            "finn_ads": True,
        },
    )

    return as_product_model(prisma_product)


def update_product(id: int, product: Product):
    prisma.product.update(
        where={"id": id},
        data={
            "name": product.name,
            "description": product.description,
            "brand": product.brand,
            "finn_query": product.finn_query,
            "image": product.image,
            "category": product.category.to_json() if product.category else "null",
        },
    )


def patch_product(
    id: int,
    name: str = None,
    description: str = None,
    brand: str = None,
    finn_query: str = None,
    image: str = None,
    category: Category = None,
):
    data = {}

    if name:
        data["name"] = name

    if description:
        data["description"] = description

    if brand:
        data["brand"] = brand

    if finn_query:
        data["finn_query"] = finn_query

    if image:
        data["image"] = image

    if category:
        data["category"] = category.to_json()

    prisma.product.update(
        where={"id": id},
        data=data,
    )


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
        retailer_ids = [(r.name, r.sku) for r in product.retailers]
        if (retailer_name, sku) in retailer_ids:
            if gtin not in [g.gtin for g in product.gtins]:
                raise IdentifierChangeError()
            if mpn not in [m.mpn for m in product.mpns]:
                raise IdentifierChangeError()
            prisma_product = product
            break

    else:
        for product in prisma_products:
            if gtin in [g.gtin for g in product.gtins]:
                prisma_product = product
                break

    if gtin not in [gtin.gtin for gtin in prisma_product.gtins]:
        raise AmbiguousProductMatch(prisma_product.id)

    return as_product_model(prisma_product)


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

    try:
        existing = find_existing_product(
            gtin=gtin,
            mpn=mpn,
            retailer_name=retailer_name,
            sku=sku,
        )

        if not existing:
            return insert_product(product)
    except AmbiguousProductMatch as e:
        prisma_product = prisma.product.find_unique(
            where={"id": e.conflicting_product_id},
        )

        root_id = prisma_product.ambiguous_to_id or prisma_product.id
        return insert_product(product, ambiguous_to_id=root_id)

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
                            "url": r.url,
                        }
                        for r in retailers_to_add
                    ],
                },
            },
        )

    product_id: int = existing.id
    return product_id


def get_ambiguous_products(product_id: int):
    prisma_product = prisma.product.find_unique(
        where={"id": product_id},
        include={
            "mpns": True,
            "gtins": True,
            "retailers": True,
            "ambiguities": {
                "include": {
                    "mpns": True,
                    "gtins": True,
                    "retailers": True,
                },
            },
            "ambiguous_to": {
                "include": {
                    "mpns": True,
                    "gtins": True,
                    "retailers": True,
                    "ambiguities": {
                        "include": {
                            "mpns": True,
                            "gtins": True,
                            "retailers": True,
                        },
                    },
                },
            },
        },
    )

    if prisma_product.ambiguous_to:
        root = prisma_product.ambiguous_to
        children = prisma_product.ambiguous_to.ambiguities
        return as_product_model(root), [as_product_model(c) for c in children]

    root = prisma_product
    children = prisma_product.ambiguities
    return as_product_model(root), [as_product_model(c) for c in children]


def insert_pending_urls(domain: str, urls: Iterable[str]):
    return prisma.pendingurl.create_many(
        [
            {
                "domain": domain,
                "url": url,
            }
            for url in urls
        ],
        skip_duplicates=True,
    )


def fetch_pending_urls(domain: str, limit=10):
    prisma_urls = prisma.pendingurl.find_many(
        where={"domain": domain},
        take=limit,
    )

    return [u.url for u in prisma_urls], [u.id for u in prisma_urls]


def delete_pending_urls(ids: list[str]):
    return prisma.pendingurl.delete_many(
        where={
            "id": {"in": ids},
        },
    )


def count_pending_urls(domain: str) -> int:
    return prisma.pendingurl.count(
        where={
            "domain": domain,
        },
    )


def upsert_finn_ads(finn_ads: list[FinnAd]):
    prisma.finnad.create_many(
        [
            {
                "id": ad.id,
                "image": ad.image,
                "lat": ad.lat,
                "lng": ad.lng,
                "price": ad.price,
                "timestamp": ad.timestamp,
                "title": ad.title,
                "product_id": ad.product_id,
            }
            for ad in finn_ads
        ],
        skip_duplicates=True,
    )


def fetch_finn_ads(product_id: int):
    prisma_finn_ads = prisma.finnad.find_many(where={"product_id": product_id})
    return [
        FinnAd(
            lng=ad.lng,
            lat=ad.lat,
            title=ad.title,
            timestamp=ad.timestamp,
            id=ad.id,
            image=ad.image,
            price=ad.price,
            product_id=ad.product_id,
        )
        for ad in prisma_finn_ads
    ]


def patch_finn_ad(
    id: int,
    price: int = None,
    title: str = None,
    image: str = None,
    relevance: float = None,
):
    data = {}

    if price:
        data["price"] = price

    if title:
        data["title"] = title

    if image:
        data["image"] = image

    if relevance:
        data["relevance"] = relevance

    prisma.finnad.update(
        where={"id": id},
        data=data,
    )


def fetch_products_with_finn_query(skip: int = 0, page_size: int = 10):
    prisma_products = prisma.product.find_many(
        where={
            "finn_query": {"not": None},
        },
        take=page_size,
        skip=skip,
        include={
            "gtins": True,
            "mpns": True,
            "retailers": True,
            "finn_ads": True,
        },
    )

    return [as_product_model(p) for p in prisma_products]


def count_products_with_finn_query():
    return prisma.product.count(
        where={
            "finn_query": {"not": None},
        },
    )


def clear_tables():
    prisma.product.delete_many()


def count_products():
    return prisma.product.count()
