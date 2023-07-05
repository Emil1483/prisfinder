import os
from time import sleep, time
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.services.mongo_service import upload_products
from src.helpers.exceptions import NotAProductPage
from src.helpers.import_tools import import_scraper
from src.helpers.find_urls import find_urls
from src.models.url import URL, URLStatus
from src.helpers.thread import concurrent_threads
from src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
)


def run():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    # TODO: create context manager
    driver = webdriver.Chrome(options)
    while True:
        try:
            with Provisioner() as p:
                # TODO: respect robots.txt
                scrape = import_scraper(p.key.domain)
                for url in p.iter_urls(URLStatus.WAITING):
                    if url is None:
                        # TODO: switch to failed urls
                        print("Empty Cursor. Disabling")
                        p.disable()
                        break

                    print(url)

                    try:
                        start = time()
                        driver.get(url.value.url)
                        end = time()

                        try:
                            products = scrape(driver)
                            upload_products(products)

                        except NotAProductPage:
                            pass

                        urls_str = find_urls(driver, p.key.domain)
                        urls = [URL.from_url_string(s) for s in urls_str]

                        p.append_urls(urls, URLStatus.WAITING)

                        p.complete_url(url, URLStatus.WAITING)
                    except Exception as e:
                        print(f"failed for url", url)
                        print(e)
                        print(traceback.format_exc())
                        p.fail_url(url, URLStatus.WAITING)

        except CouldNotFindProvisioner as e:
            print(f"{type(e).__name__} {e}: sleeping...")
            sleep(10)

        except TakeOver:
            print("Warning: TakeOver")
            continue


if __name__ == "__main__":
    THREAD_COUNT = int(os.getenv("THREAD_COUNT", "1"))
    if THREAD_COUNT > 1:
        concurrent_threads(run, thread_count=THREAD_COUNT)
    else:
        run()
