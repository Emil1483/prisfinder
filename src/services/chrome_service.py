from abc import ABC, abstractmethod
from time import sleep
from typing import Iterable
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
        return [*iter_urls(domain, self.content)]


class SeliniumClient(WebPageClient):
    def setup(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

        self._driver = webdriver.Chrome(options)
        return self

    def teardown(self):
        self._driver.quit()

    def get(self, url: str):
        try:
            return self._driver.get(url)
        except Exception as e:
            print("WARNING", type(e), type(e).__name__, e)
            self._driver.quit()
            self.__enter__()
            return self.get(url)

    def content(self):
        return self._driver.page_source

    def find_links(self, domain: str):
        n = 0
        i = 0
        for _ in range(100):
            if i >= 4:
                break

            sleep(0.1)
            url_count = len([*iter_urls("power.no", self._driver.page_source)])
            if url_count > n:
                n = url_count
                i = 0
            else:
                i += 1

        return list(dict.fromkeys(iter_urls(domain, self._driver.page_source)))


# TODO: implement Playwright https://playwright.dev/python/docs/intro
# https://www.linkedin.com/pulse/web-scraping-using-playwright-python-javascript-scrape-hero/
