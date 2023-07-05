import os
from dotenv import load_dotenv
from redis import Redis

from src.helpers.misc import hash_string
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue
from src.models.url import URL, URLKey, URLValue


def push_komplett():
    load_dotenv()

    with Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")) as r:
        pipe = r.pipeline()

        for key in r.scan_iter():
            pipe.delete(key)

        url_str = "https://www.power.no/tv-og-lyd/hodetelefoner/true-wireless-hodetelefoner/samsung-galaxy-buds2-pro-true-wireless-bora-purple/p-1646111/"
        domain = "power.no"
        url_id = hash_string(url_str)

        provisioner_value = ProvisionerValue(
            cursor_waiting=url_id,
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


if __name__ == "__main__":
    push_komplett()
