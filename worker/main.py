from time import sleep, time

from redis import Redis

from worker.src.models.url import URL, URLKey, URLValue
from worker.src.helpers.thread import concurrent_threads
from worker.src.models.provisioner import ProvisionerKey, ProvisionerValue
from worker.src.services.provisioner import (
    CouldNotFindProvisioner,
    Provisioner,
    TakeOver,
    URLExists,
)


def populate_test():
    r = Redis()
    pipe = r.pipeline()

    for key in r.scan_iter():
        pipe.delete(key)

    domain = "example.com"

    provisioner_value = ProvisionerValue(
        cursor="000",
        last_scrapet=None,
    )

    provisioner_key = ProvisionerKey(
        domain=domain,
        on=False,
    )

    pipe.set(str(provisioner_key), provisioner_value.to_json())

    for i in range(3):
        url_id = f"{i:03d}"
        next_id = (i + 1) % 3
        next_id = f"{next_id:03d}"
        prev_id = (i - 1) % 3
        prev_id = f"{prev_id:03d}"

        url = URL(
            key=URLKey(
                domain=domain,
                id=url_id,
            ),
            value=URLValue(
                url=f"https://www.{domain}/{url_id}",
                next=next_id,
                prev=prev_id,
            ),
        )

        pipe.set(str(url.key), url.value.to_json())

    pipe.execute()
    r.close()


def run():
    while True:
        try:
            start = time()
            with Provisioner() as p:
                # p.append_url(f"https://www.{p.key.domain}/appended")
                for url in p.iter_urls():
                    print(url)
                    sleep(0.1)

                    if len(url.key.id) == 3:
                        try:
                            p.append_urls(
                                [
                                    f"https://www.{p.key.domain}/appended-by/{url.key.id}/0",
                                    f"https://www.{p.key.domain}/appended-by/{url.key.id}/1",
                                    f"https://www.{p.key.domain}/appended-by/{url.key.id}/2",
                                ]
                            )
                        except URLExists as e:
                            pass
                            # end = time()
                            # print(end - start)
                            # quit()

                    # loader = loaders.ProgressLoader(total=50)
                    # for i in range(50):
                    #     loader.progress(i)
                    #     sleep(0.1)
                    # print()

        except CouldNotFindProvisioner as e:
            print(f"{type(e).__name__} {e}: sleeping...")
            sleep(10)

        except TakeOver:
            print("Warning: TakeOver")
            continue


if __name__ == "__main__":
    populate_test()
    # concurrent_threads(run, thread_count=1)
    run()
