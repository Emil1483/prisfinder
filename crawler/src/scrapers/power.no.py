from pprint import pprint

from src.services.web_page_service import (
    ClientTester,
    PlayWrightClient,
)
import src.helpers.auto_scrape as auto_scraper
from src.helpers.exceptions import NotAProductPage
from src.models.product import Product, Retailer


def scrape(url: str, content):
    auto_scraped = auto_scraper.parse(content)
    product_jsons = auto_scraped.get("jsonld", {}).get("Product", None)

    if not product_jsons:
        raise NotAProductPage()

    product_json = product_jsons[0]

    breadcrumb_list = auto_scraped["jsonld"]["BreadcrumbList"]
    breadcrumbs = [b["name"] for b in breadcrumb_list[0]["itemListElement"]]
    category = "/".join(breadcrumbs[:-1])

    image = product_json["image"]
    if image:
        image = image[0]

    yield Product(
        name=product_json["name"],
        description=product_json["description"],
        image=image,
        brand=product_json["brand"]["name"],
        gtins=[product_json["gtin13"]],
        mpns=[product_json["mpn"]],
        retailers=[
            Retailer(
                name="power",
                category=category,
                price=product_json["offers"]["price"],
                sku=str(product_json["sku"]),
                url=url,
            ),
        ],
    )


if __name__ == "__main__":
    url = "https://www.power.no/mobil-og-foto/smartklokker-og-wearables/sportsklokke/garmin-forerunner-245-sportsklokke-svart/p-1139441/"

    with ClientTester(PlayWrightClient()) as web:
        content = web.get(url)
        pprint([*scrape(url, content)])
