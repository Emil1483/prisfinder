from dataclasses import dataclass
import json
from datetime import datetime, timedelta
from math import floor
import os
from typing import Tuple
from urllib.parse import urlparse
from uuid import uuid4

from src.services.mongo_service import fetch_pending_urls
from src.helpers.misc import timestamp
from src.models.provisioner import (
    ProvisionerKey,
    ProvisionerStatus,
    ProvisionerValue,
)
from src.models.url import URL, FailedURLKey, URLKey, URLValue
from src.services.redis_service import CustomRedis


class CouldNotFindProvisioner(Exception):
    pass


class AlreadyClaimed(CouldNotFindProvisioner):
    pass


class AlreadyClosed(Exception):
    pass


class TakeOver(Exception):
    pass


@dataclass()
class ExitProvisioner(Exception):
    reason: str


class Provisioner:
    def __init__(self, timeout=timedelta(minutes=5)):
        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

        self.timeout = timeout
        self.r = CustomRedis.from_url(REDIS_URL)
        self.id = uuid4().hex
        self.disabled = False

    def __str__(self) -> str:
        return f"(key: {self.key}, value: {self.value})"

    def __enter__(self):
        self.key, self.value = self.find_provisioner()
        print(f"claimed provisioner {self}")
        self.cursor = self.fetch_url(self.value.cursor)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"exiting provisioner {self}")
        pipe = self.r.pipeline()

        value = self.r.get(str(self.key))

        if not value:
            print("Warning: Already Closed")
            return

        new_key = self.key.set_status(
            ProvisionerStatus.DISABLED if self.disabled else ProvisionerStatus.OFF
        )
        pipe.set(str(new_key), value)
        pipe.delete(str(self.key))

        _, del_count = pipe.execute()

        if del_count == 0:
            raise AlreadyClosed()

        self.r.quit()

    def disable(self):
        self.disabled = True

    def time_id(self, current_time: datetime = None):
        if not current_time:
            current_time = datetime.now()

        time_passed = current_time - datetime(
            year=current_time.year,
            month=current_time.month,
            day=current_time.day,
        )

        return floor(time_passed / self.timeout)

    def update_key(self, old_key_str: str = None):
        if old_key_str:
            old_key = ProvisionerKey.from_string(old_key_str)
        else:
            old_key = self.key

        return ProvisionerKey(
            domain=old_key.domain,
            status=ProvisionerStatus.ON,
            provisioner_id=self.id,
            time_id=self.time_id(),
        )

    def find_provisioner(self):
        print("finding provisioner...")

        domain = os.getenv("DOMAIN")

        def gen_keys():
            if domain:
                yield from self.r.scan_iter(f"provisioner:off:{domain}")
            else:
                yield from self.r.scan_iter("provisioner:off:finn.no")
                yield from self.r.scan_iter("provisioner:off:*")

            max_id = floor(timedelta(days=1) / self.timeout)
            for i in range(2, max_id):
                time_id = self.time_id(datetime.now() - i * self.timeout)

                if domain:
                    yield from self.r.scan_iter(f"provisioner:on:{time_id}:{domain}")
                else:
                    yield from self.r.scan_iter(f"provisioner:on:{time_id}:finn.no")
                    yield from self.r.scan_iter(f"provisioner:on:{time_id}:*")

        for provisioner_key in gen_keys():
            try:
                key = provisioner_key.decode()
                print(f"attempting to claim provisioner with key {key}")
                return self.claim_provisioner(key)
            except AlreadyClaimed as e:
                print(type(e), e)
                continue

        raise CouldNotFindProvisioner()

    def claim_provisioner(
        self, key_str: str
    ) -> Tuple[ProvisionerKey, ProvisionerValue]:
        pipe = self.r.pipeline()

        provisioner = self.r.get(key_str)

        if not provisioner:
            raise AlreadyClaimed(
                "Could not find provisioner. Key was probably modified by another worker"
            )

        provisioner_json = json.loads(provisioner)

        value: ProvisionerValue = ProvisionerValue.from_dict(provisioner_json)

        if value.last_scraped:
            age = timestamp() - value.last_scraped
            age_timedelta = timedelta(milliseconds=age)
            print(f"claiming provisioner with age {age_timedelta}")

            old = age_timedelta < self.timeout

            if "on" in key_str.split(":") and old:
                raise AlreadyClaimed(f"Last scraped was only {age_timedelta} ago")

        new_key = self.update_key(key_str)
        pipe.set(str(new_key), provisioner)
        pipe.delete(key_str)

        _, del_count = pipe.execute()

        if del_count == 0:
            self.r.delete(str(new_key))
            raise AlreadyClaimed(
                "Could not modify key. Key was probably modified by another worker"
            )

        return new_key, value

    def fetch_urls(self, url_ids: list[str] = None, should_raise=True) -> list[URL]:
        assert not self.disabled

        pipe = self.r.pipeline()

        url_keys = [
            URLKey(
                domain=self.key.domain,
                id=url_id,
            )
            for url_id in url_ids
        ]

        for url_key in url_keys:
            pipe.get(str(url_key))

        url_value_jsons = pipe.execute()

        urls = []
        for url_key, url_value_json in zip(url_keys, url_value_jsons):
            if not url_value_json:
                if should_raise:
                    raise ValueError(f'URL with id "{url_key}" does not exist')

                urls.append(None)
                continue

            urls.append(
                URL(
                    key=url_key,
                    value=URLValue.from_json(url_value_json),
                )
            )

        return urls

    def fetch_url(self, url_id: str, should_raise=True) -> URL:
        return self.fetch_urls([url_id], should_raise=should_raise)[0]

    def move_cursor(self) -> ProvisionerValue:
        self.cursor = self.fetch_url(self.cursor.value.next)
        self.value.cursor = self.cursor.value.next
        self.value.last_scraped = timestamp()

    def iter_urls(self):
        assert not self.disabled
        while True:
            yield self.cursor

            assert not self.disabled

            self.move_cursor()

            pipe = self.r.pipeline()
            pipe.delete(str(self.key))
            self.key = self.update_key()
            pipe.set(
                str(self.key),
                self.value.to_json(),
            )

            result = pipe.execute()

            del_count = result[0]
            if del_count == 0:
                self.r.delete(str(self.key))
                raise TakeOver(
                    "Could not modify key. Provisioner was probably claimed by another worker"
                )

    def all_urls(self):
        start_id = self.cursor.key.id
        for url in self.iter_urls():
            yield url
            if url.value.next == start_id:
                break

    def all_failed_urls(self):
        for key in self.r.scan_iter(f"failed_url:{self.key.domain}:*"):
            url_id = key.decode().split(":")[-1]
            url_key = URLKey(domain=self.key.domain, id=url_id)
            url_value = URLValue.from_json(self.r.get(str(url_key)))
            yield URL(
                key=url_key,
                value=url_value,
            )

    def append_urls(self, urls: list[URL]):
        assert not self.disabled
        assert len(urls) == len(list(dict.fromkeys([url.value.url for url in urls])))
        assert all(u.key.domain == self.key.domain for u in urls)

        def filter_urls_by_domain(urls: list[URL]):
            results = []
            for url in urls:
                domain = urlparse(url.value.url).netloc
                domain = domain.replace("www.", "")
                if domain == self.key.domain:
                    results.append(url)
            return results

        filtered_urls = filter_urls_by_domain(urls)

        def filter_unique_urls(urls: list[URL]):
            pipe = self.r.pipeline()
            for url in urls:
                pipe.get(str(url.key))

            results = pipe.execute()
            unique_urls = [u for u, r in zip(urls, results) if not r]
            return unique_urls

        unique_urls = filter_unique_urls(filtered_urls)

        if len(unique_urls) == 0:
            return

        def order_urls(urls: list[URL]):
            if len(urls) == 1:
                return

            for url, next_url in zip(urls[:-1], urls[1:]):
                url.value.next = next_url.key.id

        order_urls(unique_urls)

        pipe = self.r.pipeline()

        unique_urls[-1].value.next = self.cursor.value.next
        self.cursor.value.next = unique_urls[0].key.id

        pipe.set(str(self.cursor.key), self.cursor.value.to_json())

        for url in unique_urls:
            pipe.set(str(url.key), url.value.to_json())

        pipe.execute()

    def append_url(self, url: URL):
        return self.append_urls([url])

    def append_pending_urls(self):
        pending_urls = [
            URL.from_string(u, self.key.domain)
            for u in fetch_pending_urls(self.key.domain, limit=100)
        ]

        if pending_urls:
            self.append_urls(pending_urls)
        else:
            self.disable()
            raise ExitProvisioner("No more urls to scrape.")

    def set_scraped(self, url: URL):
        url.value.scraped_at = timestamp()
        success = self.r.set(str(url.key), url.value.to_json())

        assert success

    def fail_url(self, url: URL):
        url.value.failed_at = timestamp()
        failed_url_key = FailedURLKey.from_url_key(url.key)

        pipe = self.r.pipeline()
        pipe.set(str(url.key), url.value.to_json())
        pipe.set(str(failed_url_key), b"")

        results = pipe.execute()
        assert all(results)
