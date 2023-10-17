from dataclasses import asdict
from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Column,
    Integer,
    String,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql.schema import MetaData

import src.models.product as models


Base = declarative_base()
meta: MetaData = Base.metadata


class ProductRetailer(Base):
    __tablename__ = "product_retailers"

    id = Column(String, primary_key=True)
    name = Column(String)
    price = Column(Float)
    sku = Column(String, index=True)
    url = Column(String)
    category = Column(String)

    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="retailers")

    @classmethod
    def from_model(cls, retailer: models.Retailer):
        return ProductRetailer(
            id=f"{retailer.name}:{retailer.sku}",
            name=retailer.name,
            price=retailer.price,
            sku=retailer.sku,
            url=retailer.url,
            category=retailer.category,
        )


class ProductMPN(Base):
    __tablename__ = "product_mpns"

    id = Column(Integer, primary_key=True)
    mpn = Column(String, index=True)

    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="mpns")


class ProductGTIN(Base):
    __tablename__ = "product_gtins"

    id = Column(Integer, primary_key=True)
    gtin = Column(String, unique=True, index=True)

    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="gtins")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    image = Column(String, nullable=False)
    brand = Column(String)
    category = Column(JSON)

    retailers = relationship("ProductRetailer", back_populates="product")
    mpns = relationship("ProductMPN", back_populates="product")
    gtins = relationship("ProductGTIN", back_populates="product")

    @classmethod
    def from_model(cls, product: models.Product):
        result = Product(
            name=product.name,
            brand=product.brand,
            description=product.description,
            image=product.image,
            category=asdict(product.category) if product.category else None,
        )

        for retailer in product.retailers:
            result.retailers.append(
                ProductRetailer.from_model(retailer),
            )

        for mpn in product.mpns:
            result.mpns.append(ProductMPN(mpn=mpn))

        for gtin in product.gtins:
            result.gtins.append(ProductGTIN(gtin=gtin))

        return result

    def as_model(self):
        return models.Product(
            name=self.name,
            description=self.description,
            brand=self.brand,
            image=self.image,
            category=self.category,
            gtins=[gtin.gtin for gtin in self.gtins],
            mpns=[mpn.mpn for mpn in self.mpns],
            retailers=[
                models.Retailer(
                    name=retailer.name,
                    category=retailer.category,
                    price=retailer.price,
                    sku=retailer.sku,
                    url=retailer.url,
                )
                for retailer in self.retailers
            ],
        )


def create_tables():
    from src.services.posgres_service.postgres_service import engine

    meta.drop_all(engine)
    meta.create_all(engine)


if __name__ == "__main__":
    create_tables()
