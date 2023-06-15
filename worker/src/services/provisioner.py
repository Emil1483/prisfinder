import json
from datetime import datetime, timedelta
from math import floor
from typing import Tuple
from urllib.parse import urlparse
from uuid import uuid4

from worker.src.helpers.misc import hash_string, timestamp
from worker.src.models.provisioner import (
    ProvisionerKey,
    ProvisionerStatus,
    ProvisionerValue,
)
from worker.src.models.url import URL, URLKey, URLValue
from worker.src.services.redis_service import CustomRedis


class CouldNotFindProvisioner(Exception):
    pass


class AlreadyClaimed(CouldNotFindProvisioner):
    pass


class AlreadyClosed(Exception):
    pass


class TakeOver(Exception):
    pass


class Provisioner:
    def __init__(self, timeout=timedelta(minutes=5)):
        self.timeout = timeout
        self.r = CustomRedis()
        self.id = uuid4().hex
        self.disabled = False

    def __str__(self) -> str:
        return f"(key: {self.key}, value: {self.value})"

    def __enter__(self):
        self.key, self.value = self.find_provisioner()
        print(f"claimed provisioner {self}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("EXIT CALLED")
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
        print([*self.r.scan_iter("provisioner*")])

        def gen_keys():
            yield from self.r.scan_iter("provisioner:off:*")

            max_id = floor(timedelta(days=1) / self.timeout)
            for i in range(2, max_id):
                time_id = self.time_id(datetime.now() - i * self.timeout)
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

        if value.last_scrapet:
            age = timestamp() - value.last_scrapet
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

    def fetch_urls(self, url_ids: list[str] = None) -> list[URL]:
        assert not self.disabled

        pipe = self.r.pipeline()

        url_keys = [
            URLKey(
                domain=self.key.domain,
                id=url_id or self.value.cursor,
            )
            for url_id in url_ids
        ]

        for url_key in url_keys:
            pipe.get(str(url_key))

        url_value_jsons = pipe.execute()

        urls = []
        for url_key, url_value_json in zip(url_keys, url_value_jsons):
            if not url_value_json:
                raise ValueError(f'URL with id "{url_key}" does not exist')

            url = URL(
                key=url_key,
                value=URLValue.from_json(url_value_json),
            )

            urls.append(url)

        return urls

    def fetch_url(self, url_id: str = None) -> URL:
        return self.fetch_urls([url_id or self.value.cursor])[0]

    def iter_urls(self):
        assert not self.disabled
        while True:
            url = self.fetch_url()
            self.value = self.value.copy_with(
                last_scrapet=timestamp(),
                cursor=url.value.next,
            )

            yield url

            assert not self.disabled

            url = self.fetch_url(url.key.id)

            pipe = self.r.pipeline()

            pipe.delete(str(self.key))

            self.key = self.update_key()

            pipe.set(
                str(self.key),
                self.value.to_json(),
            )

            pipe.set(
                str(url.key),
                url.value.copy_with(scrapet_at=timestamp()).to_json(),
            )

            result = pipe.execute()

            del_count = result[0]
            if del_count == 0:
                self.r.delete(str(self.key))
                raise TakeOver(
                    "Could not modify key. Provisioner was probably claimed by another worker"
                )

    def append_urls(self, urls_str: list[str]):
        assert not self.disabled
        assert len(urls_str) == len(list(dict.fromkeys(urls_str)))

        pipe = self.r.pipeline()
        for url_str in urls_str:
            url_domain = urlparse(url_str).netloc.replace("www.", "")
            assert url_domain == self.key.domain

            key = URLKey(
                domain=url_domain,
                id=hash_string(url_str),
            )

            pipe.get(str(key))

        results = pipe.execute()

        for url_str, result in zip(urls_str, results):
            if result:
                print(f'WARNING: URL "{url_str}" already exists')

        urls_str = [u for u, r in zip(urls_str, results) if not r]

        if len(urls_str) == 0:
            return

        url_at_cursor = self.fetch_url()
        prev_url_id = url_at_cursor.value.prev
        prev_url = self.fetch_url(prev_url_id)

        url_ids = [prev_url_id, *map(hash_string, urls_str), url_at_cursor.key.id]

        urls: list[URL] = []

        for url_str, url_id, prev_id, next_id in zip(
            urls_str, url_ids[1:-1], url_ids[:-2], url_ids[2:]
        ):
            url_domain = urlparse(url_str).netloc.replace("www.", "")
            assert url_domain == self.key.domain

            url = URL(
                key=URLKey(
                    domain=url_domain,
                    id=url_id,
                ),
                value=URLValue(
                    url=url_str,
                    prev=prev_id,
                    next=next_id,
                ),
            )

            urls.append(url)

        self.value = self.value.copy_with(cursor=urls[0].key.id)

        pipe = self.r.pipeline()

        pipe.set(
            str(prev_url.key),
            prev_url.value.copy_with(next_id=urls[0].key.id).to_json(),
        )

        pipe.set(
            str(url_at_cursor.key),
            url_at_cursor.value.copy_with(prev_id=urls[-1].key.id).to_json(),
        )

        for url in urls:
            pipe.set(
                str(url.key),
                url.value.to_json(),
            )

        pipe.set(
            str(self.key),
            self.value.to_json(),
        )

        pipe.execute()

    def append_url(self, url_str: str):
        return self.append_urls([url_str])
