import src.helpers.auto_scrape as auto_scraper
from src.helpers.exceptions import NotAProductPage
from src.models.product import Product, Retailer
from src.services.chrome_service import ChromeService


def scrape(driver: ChromeService):
    auto_scraped = auto_scraper.parse(driver.page_source)
    product_jsons = auto_scraped.get("jsonld", {}).get("Product", None)

    if not product_jsons:
        raise NotAProductPage()

    product_json = product_jsons[0]

    breadcrumb_list = auto_scraped["jsonld"]["BreadcrumbList"]
    breadcrumbs = [b["name"] for b in breadcrumb_list[0]["itemListElement"]]
    category = "/".join(breadcrumbs[:-1])

    yield Product(
        name=product_json["name"],
        description=product_json["description"],
        image=product_json["image"],
        brand=product_json["brand"]["name"],
        gtins=[product_json["gtin13"]],
        mpns=[product_json["mpn"]],
        retailers=[
            Retailer(
                name="power",
                category=category,
                price=product_json["offers"]["price"],
                sku=str(product_json["sku"]),
                url=driver.current_url,
            ),
        ],
    )
