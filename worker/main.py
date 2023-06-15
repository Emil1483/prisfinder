import os
from time import sleep, time
from urllib.parse import urlparse

from redis import Redis
import requests
from worker.src.helpers.misc import hash_string
from bs4 import BeautifulSoup

from worker.src.models.url import URL, URLKey, URLValue
from worker.src.helpers.thread import concurrent_threads
from worker.src.models.provisioner import (
    ProvisionerKey,
    ProvisionerStatus,
    ProvisionerValue,
)
from worker.src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
)


def populate_test():
    r = Redis()
    pipe = r.pipeline()

    for key in r.scan_iter():
        pipe.delete(key)

    url_str = "https://www.komplett.no/"
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
                for url in p.iter_urls():
                    print(url)

                    if url.value.scrapet_at:
                        p.disable()
                        break

                    start = time()
                    response = requests.get(
                        url.value.url,
                        headers={
                            "User-Agent": "PostmanRuntime/7.32.2",
                        },
                    )
                    end = time()
                    sleep(10 * (end - start))

                    url_path = url.value.url.split(p.key.domain)[-1]

                    if url_path and url_path[-1] == "/":
                        url_path = url_path[:-1]

                    url_path = url_path.replace("?", "qmark")

                    name = f"data/{p.key.domain}{url_path}.html"
                    directory, _ = os.path.split(name)

                    if directory:
                        os.makedirs(directory, exist_ok=True)

                    with open(name, "w") as f:
                        f.write(response.text)

                    def gen_new_urls():
                        soup = BeautifulSoup(response.content, "html.parser")
                        for a in soup.find_all("a"):
                            href = a.get("href")
                            if not href:
                                continue
                            if href == "#":
                                continue

                            if "http" in href:
                                domain = urlparse(href).netloc.replace("www.", "")
                                if domain == p.key.domain:
                                    yield href
                            else:
                                url = f"https://www.{p.key.domain}{href}"
                                url_domain = urlparse(url).netloc.replace("www.", "")
                                if url_domain == p.key.domain:
                                    yield url

                    new_urls = [*gen_new_urls()]
                    p.append_urls(list(dict.fromkeys(new_urls)))

        except CouldNotFindProvisioner as e:
            print(f"{type(e).__name__} {e}: sleeping...")
            sleep(10)

        except TakeOver:
            print("Warning: TakeOver")
            continue


if __name__ == "__main__":
    # populate_test()
    # concurrent_threads(run, thread_count=1)
    run()
