from src.models.product import Product, Retailer
from src.helpers.exceptions import NotAProductPage
import src.helpers.auto_scrape as auto_scraper


def scrape(url: str, content):
    auto_scraped = auto_scraper.parse(content)
    product_jsons = auto_scraped.get("jsonld", {}).get("Product", None)

    if not product_jsons:
        raise NotAProductPage()

    product_json = product_jsons[0]

    yield Product(
        name=product_json["name"],
        description=product_json["description"],
        image=product_json["image"],
        brand=product_json["brand"]["name"],
        gtins=[product_json["gtin13"]],
        mpns=[product_json["mpn"]],
        retailers=[
            Retailer(
                name="localhost",
                category="no_category",
                price=product_json["offers"]["price"],
                sku=str(product_json["sku"]),
                url=url,
            ),
        ],
    )
