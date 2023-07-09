from redis import Redis
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue

from src.models.url import URL, URLKey, URLValue


def populate_test():
    r = Redis()
    pipe = r.pipeline()

    for key in r.scan_iter():
        pipe.delete(key)

    domain = "example.com"

    paths = [f"/products/{i}" for i in range(10)]
    paths[6] = "/fail"

    urls: list[URL] = []
    for i in range(len(paths)):
        prev_i = (i - 1) % len(paths)
        next_i = (i + 1) % len(paths)

        prev_path = paths[prev_i]
        next_path = paths[next_i]
        path = paths[i]

        urls.append(
            URL(
                key=URLKey(
                    domain=domain,
                    id=str(i),
                ),
                value=URLValue(
                    url=f"https://{domain}{path}",
                    next=str(next_i),
                    prev=str(prev_i),
                ),
            )
        )

    for url in urls:
        pipe.set(str(url.key), url.value.to_json())

    provisioner_value = ProvisionerValue(
        cursor_waiting=urls[0].key.id,
        last_scrapet=None,
    )

    provisioner_key = ProvisionerKey(
        domain=domain,
        status=ProvisionerStatus.OFF,
    )

    pipe.set(str(provisioner_key), provisioner_value.to_json())

    pipe.execute()
    r.close()
