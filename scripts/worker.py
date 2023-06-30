import os
from time import sleep, time
from urllib.parse import urlparse

from redis import Redis
import requests

from src.services.mongo_service import upload_products
from src.helpers.exceptions import NotAProductPage
from src.helpers.import_tools import import_scraper
from src.helpers.iter_urls import iter_urls
from src.helpers.misc import hash_string
from src.models.url import URL, URLKey, URLValue
from src.helpers.thread import concurrent_threads
from src.models.provisioner import (
    ProvisionerKey,
    ProvisionerStatus,
    ProvisionerValue,
)
from src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
)


def populate_test():
    r = Redis()
    pipe = r.pipeline()

    for key in r.scan_iter():
        pipe.delete(key)

    url_str = "https://www.komplett.no/product/1179971"
    domain = "komplett.no"
    url_id = hash_string(url_str)

    provisioner_value = ProvisionerValue(
        cursor=url_id,
        last_scrapet=None,
    )

    provisioner_key = ProvisionerKey(
        domain=domain,
        status=ProvisionerStatus.OFF,
    )

    pipe.set(str(provisioner_key), provisioner_value.to_json())

    url = URL(
        key=URLKey(
            domain=domain,
            id=url_id,
        ),
        value=URLValue(
            url=url_str,
            next=url_id,
            prev=url_id,
        ),
    )

    pipe.set(str(url.key), url.value.to_json())

    pipe.execute()
    r.close()


def run():
    while True:
        try:
            with Provisioner() as p:
                scrape = import_scraper(p.key.domain)
                for url in p.iter_urls():
                    print(url)

                    if url.value.scrapet_at:
                        p.disable()
                        break

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

                    p.append_urls(list(dict.fromkeys(iter_urls(response))))

                    sleep(10 * (end - start))

        except CouldNotFindProvisioner as e:
            print(f"{type(e).__name__} {e}: sleeping...")
            sleep(10)

        except TakeOver:
            print("Warning: TakeOver")
            continue


if __name__ == "__main__":
    # populate_test()
    THREAD_COUNT = int(os.getenv("THREAD_COUNT", "1"))
    if THREAD_COUNT > 1:
        concurrent_threads(run, thread_count=THREAD_COUNT)
    else:
        run()
