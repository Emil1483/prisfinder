from abc import ABC, abstractmethod
from typing import Iterable
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.models.product import Product
from src.helpers.exceptions import NotAProductPage
from src.helpers.import_tools import import_scraper


def iter_urls(domain: str, content):
    soup = BeautifulSoup(content, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        if href == "#":
            continue

        if "http" in href:
            url_domain = urlparse(href).netloc
            if url_domain == domain:
                yield str(href)
        else:
            url = f"https://{domain}{href}"
            url_domain = urlparse(url).netloc
            if url_domain == domain:
                yield url


class WebPageClient(ABC):
    @abstractmethod
    def setup(self):
        raise NotImplementedError()

    @abstractmethod
    def teardown(self):
        raise NotImplementedError()

    @abstractmethod
    def get(self, url: str):
        raise NotImplementedError()

    @abstractmethod
    def content(self) -> bytes:
        raise NotImplementedError()

    @abstractmethod
    def find_links(self, domain: str) -> Iterable[str]:
        raise NotImplementedError()


class WebPageService:
    def __init__(self, domain: str, client: WebPageClient):
        self.domain = domain
        self.client = client
        self._scrape = import_scraper(domain)
        self.current_url = None

    def __enter__(self):
        self.client.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.teardown()

    def scrape(self, url: str) -> list[Product]:
        if self._scrape is None:
            raise NotImplementedError()

        self.client.get(url)
        self.current_url = url

        try:
            return [*self._scrape(self)]
        except NotAProductPage:
            return []

    def find_links(self):
        return self.client.find_links(self.domain)


class RequestClient(WebPageClient):
    def setup(self):
        self._content = None

    def teardown(self):
        pass

    def get(self, url):
        response = requests.get(
            url,
            allow_redirects=True,
            headers={
                "User-Agent": "PostmanRuntime/7.32.3",
            },
        )
        self._content = response.content

    def content(self) -> bytes:
        return self._content

    def find_links(self, domain: str) -> Iterable[str]:
        links = [*iter_urls(domain, self.content())]
        return list(dict.fromkeys(links))


class PlayWrightClient(WebPageClient):
    def setup(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.webkit.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def teardown(self):
        self.playwright.stop()

    def get(self, url: str):
        try:
            return self.page.goto(url)
        except Exception as e:
            print("WARNING", type(e), type(e).__name__, e)
            self.teardown()
            self.setup()
            return self.page.goto(url)

    def content(self):
        return self.page.content()

    def find_links(self, domain: str):
        links = [*iter_urls(domain, self.content())]
        return list(dict.fromkeys(links))


if __name__ == "__main__":
    with WebPageService("power.no", PlayWrightClient()) as web:
        web.client.get(
            "https://www.power.no/tv-og-lyd/hodetelefoner/true-wireless-hodetelefoner/samsung-galaxy-buds2-pro-true-wireless-bora-purple/p-1646111/"
        )
        print(web.client.content())
        print(web.client.find_links("power.no"))

        web.client.get(
            "https://www.power.no/mobil-og-foto/mobiltelefon/samsung-galaxy-a54-5g-128-gb-svart/p-1940239/"
        )
        print(web.client.content())
        print(web.client.find_links("power.no"))

        web.client.get(
            "https://www.power.no/data-og-tilbehoer/skjermer/pc-skjerm/samsung-u32r591-32-4k-uhd-skjerm-hvit/p-1891792/"
        )
        print(web.client.content())
        print(web.client.find_links("power.no"))
