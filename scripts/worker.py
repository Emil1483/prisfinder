import os
from time import sleep
import traceback
from src.helpers.misc import hash_string

import src.services.finn_service as finn_service
from src.services.chrome_service import ChromeService
from src.services.mongo_service import fetch_pending_urls, upload_products
from src.helpers.exceptions import NotAProductPage
from src.helpers.import_tools import import_scraper
from src.helpers.find_urls import find_urls
from src.models.url import URL, URLKey, URLStatus, URLValue
from src.helpers.thread import concurrent_threads
from src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
)


def run():
    with ChromeService() as driver:
        while True:
            try:
                with Provisioner() as p:
                    # TODO: respect robots.txt
                    scrape = import_scraper(p.key.domain)
                    for url in p.iter_urls(URLStatus.WAITING):
                        print(url)
                        if url is None:
                            pending_urls = [
                                URL.from_string(u, p.key.domain)
                                for u in fetch_pending_urls(p.key.domain, limit=100)
                            ]

                            if pending_urls:
                                p.append_urls(pending_urls, URLStatus.WAITING)
                                continue
                            else:
                                print("Empty Cursor. Disabling")
                                p.disable()
                                break

                        try:
                            if p.key.domain == "finn.no":
                                product_id = url.value.url
                                finn_service.populate_product(product_id)
                                continue

                            driver.get(url.value.url)

                            try:
                                products = scrape(driver)
                                upload_products(products)

                            except NotAProductPage:
                                pass

                            urls_str = find_urls(driver, p.key.domain)
                            urls = [URL.from_string(u, p.key.domain) for u in urls_str]

                            p.append_urls(urls, URLStatus.WAITING)

                            p.complete_url(url, URLStatus.WAITING)
                        except Exception as e:
                            print(f"failed for url", url, e, type(e).__name__)
                            print(traceback.format_exc())
                            p.fail_url(url, URLStatus.WAITING)

            except CouldNotFindProvisioner as e:
                print(f"CouldNotFindProvisioner {e}: sleeping...")
                sleep(10)

            except TakeOver:
                print("Warning: TakeOver")
                continue


if __name__ == "__main__":
    THREAD_COUNT = int(os.getenv("THREAD_COUNT", "1"))
    if THREAD_COUNT > 1:
        print("concurrent threads")
        concurrent_threads(run, thread_count=THREAD_COUNT)
    else:
        print("single thread")
        run()
