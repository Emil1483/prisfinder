from pprint import pprint
from time import sleep
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from requests import Response
from selenium.webdriver.chrome.webdriver import WebDriver


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


def find_urls(driver: WebDriver, domain: str):
    n = 0
    i = 0
    for _ in range(100):
        if i >= 4:
            break

        sleep(0.1)
        url_count = len([*iter_urls("power.no", driver.page_source)])
        if url_count > n:
            n = url_count
            i = 0
        else:
            i += 1

    return list(dict.fromkeys(iter_urls(domain, driver.page_source)))
