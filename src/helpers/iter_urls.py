from urllib.parse import urlparse
from bs4 import BeautifulSoup
from requests import Response


def iter_urls(response: Response):
    soup = BeautifulSoup(response.content, "html.parser")

    res_url_domain = urlparse(response.url).netloc

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        if href == "#":
            continue

        if "http" in href:
            domain = urlparse(href).netloc
            if domain == res_url_domain:
                yield href
        else:
            url = f"https://{res_url_domain}{href}"
            url_domain = urlparse(url).netloc
            if url_domain == res_url_domain:
                yield url
