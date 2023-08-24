import gc
import os
import sys
from time import sleep
import traceback
import psutil

from src.services.web_page_service import WebPageService
from src.services.mongo_service import fetch_pending_urls, upload_products
from src.models.url import URL
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
                with WebPageService.from_domain(p.key.domain) as web:
                    # TODO: respect robots.txt
                    for url in p.iter_urls():
                        print(url)
                        if url.value.scraped_at:
                            # REFACTOR
                            # TODO: implement p.append_pending_urls()
                            pending_urls = [
                                URL.from_string(u, p.key.domain)
                                for u in fetch_pending_urls(p.key.domain, limit=100)
                            ]

                            if pending_urls:
                                p.append_urls(pending_urls)
                                continue
                            else:
                                print("Empty Cursor. Disabling")
                                p.disable()
                                break

                        memory_info = psutil.Process(os.getpid()).memory_info()
                        memory_usage_mb = memory_info.rss / 1024**2
                        print("Current memory usage:", memory_usage_mb, "MB")

                        try:
                            new_urls_str = web.handle_url(url.value.url)
                            new_urls = [
                                URL.from_string(u, p.key.domain) for u in new_urls_str
                            ]

                            p.append_urls(new_urls)
                            p.complete_url(url)
                        except Exception as e:
                            print(f"failed for url", url, e, type(e).__name__)
                            print(traceback.format_exc())
                            p.fail_url(url)

        except CouldNotFindProvisioner as e:
            print(f"CouldNotFindProvisioner {e}: sleeping...")
            sleep(10)
            continue

        except TakeOver:
            print("Warning: TakeOver")
            continue


if __name__ == "__main__":
    THREAD_COUNT = int(os.getenv("THREAD_COUNT", "1"))
    concurrent_workers(run, workers_count=THREAD_COUNT)
