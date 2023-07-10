import os
from time import sleep
import traceback

import psutil

from src.helpers.exceptions import ExceededMemoryLimit
from src.services.web_page_service import WebPageService
from src.services.mongo_service import fetch_pending_urls, upload_products
from src.models.url import URL, URLStatus
from src.helpers.thread import concurrent_workers
from src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
)


def run():
    while True:
        try:
            with Provisioner() as p:
                with WebPageService(p.key.domain, p.create_web_page_client()) as web:
                    # TODO: respect robots.txt
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

                        memory_info = psutil.Process(os.getpid()).memory_info()
                        memory_usage_mb = memory_info.rss / 1024**2
                        print("Current memory usage:", memory_usage_mb, "MB")

                        if memory_usage_mb > 800:
                            raise ExceededMemoryLimit()

                        try:
                            if p.key.domain == "finn.no":
                                import src.services.finn_service as finn_service

                                product_id = url.value.url
                                finn_service.populate_product(product_id)
                                continue

                            products = web.scrape(url.value.url)
                            if products:
                                upload_products(products)

                            urls_str = web.find_links()
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
            continue

        except TakeOver:
            print("Warning: TakeOver")
            continue

        except ExceededMemoryLimit:
            print("Exceeded memory limit. Restarting")
            break


if __name__ == "__main__":
    THREAD_COUNT = int(os.getenv("THREAD_COUNT", "1"))
    concurrent_workers(run, workers_count=THREAD_COUNT)
