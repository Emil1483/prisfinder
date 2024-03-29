import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from redis import Redis
from redis.client import Redis
from src.helpers.flask_error_handler import HTTPException
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue

from src.models.url import URL, FailedURLKey, URLKey, URLValue


class RedisService(Redis):
    @classmethod
    def from_env_url(cls):
        load_dotenv()
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        service: RedisService = RedisService.from_url(redis_url)
        return service

    def __enter__(self):
        service: RedisService = super().__enter__()
        return service

    def insert_provisioner(self, root_url: str, priority=2, domain: str = None):
        if not domain:
            domain = urlparse(root_url).netloc

            if domain != "127.0.0.1":
                domain = ".".join(domain.split(".")[-2:])

        existing = self.keys(f"provisioner:*:{domain}:*")
        if existing:
            print(f"provisioner with domain '{domain}' already exists")
            return

        pipe = self.pipeline()

        url = URL.from_string(root_url, domain)
        pipe.set(str(url.key), url.value.to_json())

        provisioner_key = ProvisionerKey(
            domain=domain,
            status=ProvisionerStatus.off,
            priority=priority,
        )

        provisioner_value = ProvisionerValue(cursor=url.key.id)

        pipe.set(str(provisioner_key), provisioner_value.to_json())

        pipe.execute()

    def clear_provisioners(self):
        pipe = self.pipeline()

        for provisioner_key in self.scan_provisioner_keys():
            domain = provisioner_key.domain

            for url_key_bytes in self.scan_url_keys(domain):
                pipe.delete(str(url_key_bytes))

            for url_key_bytes in self.scan_failed_url_keys(domain):
                pipe.delete(str(url_key_bytes))

            pipe.delete(str(provisioner_key))

        pipe.execute()

    def scan_provisioner_keys(self):
        for provisioner_key_bytes in self.scan_iter("provisioner:*"):
            provisioner_key = ProvisionerKey.from_string(provisioner_key_bytes.decode())

            yield provisioner_key

    def fetch_provisioner(self, domain: str) -> tuple[ProvisionerKey, ProvisionerValue]:
        keys = self.keys(f"provisioner:*:{domain}:*")
        if not keys:
            raise HTTPException(f"provisioner with domain {domain} not found", 404)

        key = ProvisionerKey.from_string(keys[0].decode())
        value_str = self.get(str(key)).decode()
        value = ProvisionerValue.from_json(value_str)

        return key, value

    def fetch_url(self, domain: str, url_id: str):
        key = URLKey(domain=domain, id=url_id)
        value_json = self.get(str(key))

        if value_json is None:
            raise KeyError(f"URL with id {url_id} not found")

        value: URLValue = URLValue.from_json(value_json)
        return key, value

    def iter_urls(self, domain: str, cursor: str):
        key, value = self.fetch_url(domain, cursor)
        yield key, value

        while value.next != cursor:
            key, value = self.fetch_url(domain, value.next)
            yield key, value

    def scan_failed_url_keys(self, domain: str):
        for key in self.scan_iter(f"failed_url:{domain}:*"):
            yield FailedURLKey.from_string(key.decode())

    def scan_url_keys(self, domain: str):
        for key in self.scan_iter(f"url:{domain}:*"):
            yield URLKey.from_string(key.decode())

    def update_provisioner_key(
        self,
        old_key: ProvisionerKey,
        new_key: ProvisionerKey,
        value: ProvisionerValue,
    ):
        pipe = self.pipeline()

        pipe.set(str(new_key), value.to_json())
        pipe.delete(str(old_key))

        _, del_count = pipe.execute()

        if del_count == 0:
            self.r.delete(str(new_key))
            raise ValueError(
                "Could not modify key. Key was probably modified by another actor"
            )

    def disable_provisioner(self, domain: str):
        old_key, value = self.fetch_provisioner(domain)

        if old_key.status == ProvisionerStatus.disabled:
            raise HTTPException("Provisioner is already disabled", 400)

        new_key = old_key.with_status(ProvisionerStatus.disabled)
        self.update_provisioner_key(old_key, new_key, value)

    def enable_provisioner(self, domain: str):
        old_key, value = self.fetch_provisioner(domain)

        if old_key.status != ProvisionerStatus.disabled:
            raise HTTPException("Provisioner is not disabled", 400)

        new_key = old_key.with_status(ProvisionerStatus.off)
        self.update_provisioner_key(old_key, new_key, value)
