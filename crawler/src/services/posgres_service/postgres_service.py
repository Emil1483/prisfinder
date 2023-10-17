import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from src.services.posgres_service.postgres_models import (
    Product,
    ProductGTIN,
    ProductMPN,
    ProductRetailer,
    meta,
)
import src.models.product as models
import logging

logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

load_dotenv()

POSTGRESQL_URI = os.getenv("POSTGRESQL_URI")
engine = create_engine(POSTGRESQL_URI)


session_maker = sessionmaker(bind=engine)
session = session_maker()


def insert_product(product: models.Product):
    sql_model = Product.from_model(product)
    session.add(sql_model)
    session.commit()


def upsert_product(product: models.Product):
    retailer_ids = [r.id for r in product.retailers]
    existing = fetch_product(
        gtins=product.gtins, mpns=product.mpns, productRetailerIds=retailer_ids
    )

    if existing:
        existing_retailer_names = [r.name for r in existing.as_model().retailers]
        retailers_to_add = [
            r for r in product.retailers if r.name not in existing_retailer_names
        ]

        gtins_to_add = [
            gtin for gtin in product.gtins if gtin not in existing.as_model().gtins
        ]

        mpns_to_add = [
            mpn for mpn in product.mpns if mpn not in existing.as_model().mpns
        ]

        if retailers_to_add or gtins_to_add or mpns_to_add:
            for retailer in retailers_to_add:
                existing.retailers.append(ProductRetailer.from_model(retailer))

            for gtin in gtins_to_add:
                existing.gtins.append(ProductGTIN(gtin=gtin))

            for mpn in mpns_to_add:
                existing.mpns.append(ProductMPN(mpn=mpn))

            session.commit()

        return

    insert_product(product)


def fetch_product(
    gtins: list[str] = None,
    mpns: list[str] = None,
    productRetailerIds: list[str] = None,
) -> Product:
    assert gtins or mpns or productRetailerIds

    def gen():
        if mpns:
            yield ProductMPN.mpn.in_(mpns)
        if gtins:
            yield ProductGTIN.gtin.in_(gtins)
        if productRetailerIds:
            yield ProductRetailer.id.in_(productRetailerIds)

    query = (
        session.query(Product)
        .outerjoin(ProductGTIN)
        .outerjoin(ProductMPN)
        .outerjoin(ProductRetailer)
        .filter(or_(*gen()))
    )

    products = query.all()
    assert len(products) <= 1

    if products:
        return products[0]
    else:
        return None


def clear_all_tables():
    for table in reversed(meta.sorted_tables):
        session.execute(table.delete())
    session.commit()
