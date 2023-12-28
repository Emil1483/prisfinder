from datetime import timedelta
from multiprocessing import Event
import os
import traceback
import psutil

from src.services.redis_service import RedisService
from src.services.web_page_service import WebPageService
from src.models.url import URL
from src.services.provisioner import (
    CouldNotFindProvisioner,
    ExitProvisioner,
    Provisioner,
    ProvisionerTooOld,
    TakeOver,
)


def default_handler(
    p: Provisioner,
    start_event: Event = None,
    service: WebPageService = None,
):
    with service or WebPageService.from_domain(p.key.domain) as web:
        if start_event:
            start_event.set()

        # TODO: respect robots.txt
        for url in p.iter_urls():
            print("handling url:", url)
            if url.visited:
                p.append_pending_urls()

            memory_info = psutil.Process(os.getpid()).memory_info()
            memory_usage_mb = memory_info.rss / 1024**2
            print("Current memory usage:", memory_usage_mb, "MB")

            try:
                new_urls_str = web.handle_url(url.value.url)
                new_urls = [URL.from_string(u, p.key.domain) for u in new_urls_str]

                p.append_urls(new_urls)
                p.set_scraped(url)
            except Exception as e:
                print(f"failed for url", url, e, type(e).__name__)
                print(traceback.format_exc())
                p.fail_url(url)


def run(
    handler=default_handler,
    *args,
    timeout=timedelta(minutes=5),
    max_age=timedelta(minutes=10),
    **kwargs,
):
    with Provisioner(timeout=timeout, max_age=max_age) as p:
        handler(p, *args, **kwargs)


if __name__ == "__main__":
    try:
        run()
    except ProvisionerTooOld:
        print("Provisioner too old, exiting")
    except CouldNotFindProvisioner:
        print("Could not find provisioner, exiting")
    except TakeOver:
        print("Someone else is handling this provisioner, exiting")
    except ExitProvisioner as e:
        print("Exiting:", e)
