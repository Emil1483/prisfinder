from dataclasses import dataclass
from html import unescape
import json
from pprint import pprint
import requests
from bs4 import BeautifulSoup
import microdata


@dataclass(order=True, frozen=True)
class ParseJsonLdException(Exception):
    error: Exception


def parse_metatags_data(soup: BeautifulSoup):
    metatags_data = {}
    meta_tags = soup.find_all("meta")

    for elem in meta_tags:
        name_key = next(
            (
                attr
                for attr in elem.attrs
                if attr in ["name", "property", "itemprop", "http-equiv"]
            ),
            None,
        )
        if name_key is not None:
            name = elem.attrs[name_key]
            value = elem.get("content")

            if name not in metatags_data:
                metatags_data[name] = []

            metatags_data[name].append(value)

    return metatags_data


def get_jsonld_data(soup: BeautifulSoup):
    jsonld_data = {}

    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        try:
            parsed_json = json.loads(unescape(script.string))
            if not isinstance(parsed_json, list):
                parsed_json = [parsed_json]
            for obj in parsed_json:
                obj_type = obj.get("@type")
                jsonld_data[obj_type] = jsonld_data.get(obj_type, [])
                jsonld_data[obj_type].append(obj)
        except Exception as e:
            raise ParseJsonLdException(e)

    return jsonld_data


def parse(content):
    soup = BeautifulSoup(content, "html.parser")
    return {
        "metatags": parse_metatags_data(soup),
        "microdata": microdata.get_items(content),
        "jsonld": get_jsonld_data(soup),
    }


if __name__ == "__main__":

    def test(url):
        response = requests.get(
            url,
            allow_redirects=True,
            headers={
                "User-Agent": "PostmanRuntime/7.32.2",
            },
        )
        return parse(response.content)

    pprint(test("https://www.komplett.no/product/1179971"))
    pprint(test("https://www.komplett.no"))
