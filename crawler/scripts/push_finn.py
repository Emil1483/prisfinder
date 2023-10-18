import os
from dotenv import load_dotenv
from redis import Redis
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue


def push_finn():
    load_dotenv()

    with Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")) as r:
        pipe = r.pipeline()
        for key in r.scan_iter("url:finn.no:*"):
            pipe.delete(key)

        for key in r.scan_iter("provisioner:*:finn.no"):
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
