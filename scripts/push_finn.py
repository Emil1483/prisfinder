import os
from dotenv import load_dotenv
from redis import Redis
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue
from src.services.mongo_service import fetch_products, insert_pending_urls


def push_finn():
    load_dotenv()

    def iter_product_ids():
        for product in fetch_products(limit=10):
            yield str(product._id)

    insert_pending_urls(domain="finn.no", urls=iter_product_ids())

    with Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")) as r:
        pipe = r.pipeline()
        for key in r.scan_iter("url:finn.no:*"):
            pipe.delete(key)

        provisioner_value = ProvisionerValue()

        provisioner_key = ProvisionerKey(
            domain="finn.no",
            status=ProvisionerStatus.OFF,
        )

        pipe.set(str(provisioner_key), provisioner_value.to_json())

        pipe.execute()


if __name__ == "__main__":
    push_finn()
