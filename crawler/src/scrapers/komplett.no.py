from pprint import pprint
from bs4 import BeautifulSoup
import requests

from src.helpers.exceptions import CouldNotScrape, NotAProductPage
from src.models.product import Product, Retailer
import src.helpers.auto_scrape as auto_scraper
from src.services.web_page_service import WebPageService


def _nested_attribute(o, attribute_names: list):
    if not attribute_names:
        return o

    def _get_attribute():
        attribute = getattr(o, attribute_names[0])
        if attribute is not None:
            return attribute

        try:
            attribute = o[attribute_names[0]]
            if isinstance(attribute, list):
                return attribute[0]
            return attribute
        except KeyError:
            pass

    attribute = _get_attribute()

    if attribute is None:
        return None

    return _nested_attribute(
        attribute,
        attribute_names[1:],
    )


def _find_element(soup: BeautifulSoup, finder: dict) -> str:
    tags = soup.find_all(finder["tag"])
    for tag in tags:
        if "where" in finder:
            child_tag, child_tag_text = finder["where"]
            attribute_names = child_tag.split(".")
            if _nested_attribute(tag, attribute_names) != child_tag_text:
                continue

        if "find" in finder:
            return _find_element(tag, finder["find"])

        return tag.text


def _find_ean(soup: BeautifulSoup) -> str:
    return _find_element(
        soup,
        {
            "tag": "table",
            "where": ("caption.text", "Generelt"),
            "find": {
                "tag": "tr",
                "where": ("th.text", "EAN"),
                "find": {
                    "tag": "td",
                },
            },
        },
    )


def _find_brand(soup: BeautifulSoup) -> str:
    brand_element = soup.find(itemprop="manufacturer")
    if brand_element:
        return brand_element.text


def _find_category(url_path: str, sku: str) -> str:
    if f"/{sku}/" not in url_path:
        raise CouldNotScrape()

    path_after_sku = url_path.split(f"/{sku}/")[-1]

    split_path = path_after_sku.split("/")
    if len(split_path) <= 1:
        raise CouldNotScrape()

    categories = split_path[:-1]
    category = "/".join(categories)
    return category


def scrape(service: WebPageService):
    auto_scraped = auto_scraper.parse(service.client.content())
    product_jsons = auto_scraped.get("jsonld", {}).get("Product", None)

    if not product_jsons:
        raise NotAProductPage()

    product_json = product_jsons[0]

    sku = product_json["sku"]
    price_str = product_json["offers"]["price"]
    price = float(price_str)

    soup = BeautifulSoup(service.client.content(), "html.parser")

    yield Product(
        name=product_json["name"],
        brand=_find_brand(soup),
        description=product_json["description"],
        gtins=[_find_ean(soup)],
        image=product_json["image"],
        mpns=[product_json["mpn"]],
        retailers=[
            Retailer(
                name="komplett",
                price=price,
                sku=sku,
                url=service.current_url,
                category=_find_category(service.current_url, sku),
            )
        ],
    )


if __name__ == "__main__":
    response = requests.get(
        "https://www.komplett.no/product/1179971/tv-lyd-bilde/hodetelefoner-tilbehoer/tilbehoer-til-hodetelefoner/elago-armor-case-galaxy-buds-2-pro-live-sort",
        allow_redirects=True,
        headers={
            "User-Agent": "PostmanRuntime/7.32.2",
        },
    )

    pprint(scrape(response))
