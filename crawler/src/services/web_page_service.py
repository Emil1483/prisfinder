from abc import ABC, abstractmethod
from typing import Iterable
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.services.prisma_service import upsert_product
from src.services.finn_service import FinnURLHandler
from src.services.url_handler import URLHandler
from src.helpers.exceptions import NotAProductPage
from src.helpers.import_tools import import_scraper


def iter_urls(base_url: str, content):
    soup = BeautifulSoup(content, "html.parser")
    domain = urlparse(base_url).netloc
    scheme = urlparse(base_url).scheme

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
            url = f"{scheme}://{domain}{href}"
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


class RequestClient(WebPageClient):
    def setup(self):
        self._content = None

    def teardown(self):
        pass

    def get(self, url):
        response = requests.get(
            url.replace("localhost", "127.0.0.1"),
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
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def teardown(self):
        self.playwright.stop()

    def get(self, url: str):
        try:
            self.page.goto(url)
            self.context.clear_cookies()
        except Exception as e:
            print("WARNING", type(e), type(e).__name__, e)
            try:
                self.teardown()
            except Exception as e:
                print("Error running teardown:", e)
            self.setup()
            self.page.goto(url)
            self.context.clear_cookies()

    def content(self):
        return self.page.content()

    def find_links(self, domain: str):
        links = [*iter_urls(domain, self.content())]
        return list(dict.fromkeys(links))


class ClientTester:
    def __init__(self, client: WebPageClient):
        self.client = client

    def __enter__(self):
        self.client.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.teardown()

    def get(self, url: str) -> bytes:
        self.client.get(url)
        return self.client.content()


class ProductURLHandler(URLHandler):
    def __init__(self, domain: str) -> list[str]:
        clients = {
            "power.no": PlayWrightClient,
        }

        self.client = clients.get(domain, RequestClient)()
        self.scrape = import_scraper(domain)
        self.domain = domain

    def handle_url(self, url: str):
        self.client.get(url)

        try:
            products = [*self.scrape(url, self.client.content())]
            for product in products:
                upsert_product(product)
        except NotAProductPage:
            print("WARNING: NotAProductPage")

        return self.client.find_links(url)

    def setup(self):
        self.client.setup()

    def teardown(self):
        self.client.teardown()


class WebPageService:
    def __init__(self, url_handler: URLHandler):
        self.url_handler = url_handler

    @classmethod
    def from_domain(cls, domain: str):
        if domain == "finn.no":
            return WebPageService(FinnURLHandler())

        return WebPageService(ProductURLHandler(domain))

    def __enter__(self):
        self.url_handler.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.url_handler.teardown()

    def handle_url(self, url: str) -> list[str]:
        return self.url_handler.handle_url(url)
