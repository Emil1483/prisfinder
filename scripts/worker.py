import os
from time import sleep, time
import traceback
import requests

from src.services.mongo_service import upload_products
from src.helpers.exceptions import NotAProductPage
from src.helpers.import_tools import import_scraper
from src.helpers.iter_urls import iter_urls
from src.models.url import URL, URLStatus
from src.helpers.thread import concurrent_threads
from src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
)


def run():
    while True:
        try:
            with Provisioner() as p:
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
                        response = requests.get(
                            url.value.url,
                            allow_redirects=True,
                            headers={
                                "User-Agent": "PostmanRuntime/7.32.2",
                            },
                            timeout=30,
                        )
                        end = time()

                        try:
                            products = scrape(response)
                            upload_products(products)

                        except NotAProductPage:
                            pass

                        urls_str = list(dict.fromkeys(iter_urls(response)))
                        urls = [URL.from_url_string(s) for s in urls_str]

                        p.append_urls(urls, URLStatus.WAITING)

                        sleep(10 * (end - start))

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
