import json
from datetime import datetime, timedelta
from math import floor
import os
from typing import Tuple
from uuid import uuid4

from src.helpers.misc import timestamp
from src.models.provisioner import (
    ProvisionerKey,
    ProvisionerStatus,
    ProvisionerValue,
)
from src.models.url import URL, URLKey, URLStatus, URLValue
from src.services.web_page_service import PlayWrightClient, RequestClient
from src.services.redis_service import CustomRedis


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

    def create_web_page_client(self):
        clients = {
            "power.no": PlayWrightClient,
        }

        return clients.get(self.key.domain, RequestClient)()

    def time_id(self, current_time: datetime = None):
        # TODO: use zulu
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
                yield from self.r.scan_iter("provisioner:off:*")

            max_id = floor(timedelta(days=1) / self.timeout)
            for i in range(2, max_id):
                time_id = self.time_id(datetime.now() - i * self.timeout)

                if domain:
                    yield from self.r.scan_iter(f"provisioner:on:{time_id}:{domain}")
                else:
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

    def fetch_urls(self, url_ids: list[str] = None, should_raise=True) -> list[URL]:
        assert not self.disabled

        pipe = self.r.pipeline()

        url_keys = [
            URLKey(
                domain=self.key.domain,
                id=url_id or self.value.cursor_waiting,
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

            url = URL(
                key=url_key,
                value=URLValue.from_json(url_value_json),
            )

            urls.append(url)

        return urls

    def fetch_url(self, url_id: str, should_raise=True) -> URL:
        return self.fetch_urls([url_id], should_raise=should_raise)[0]

    def fetch_url_at_cursor(self, url_status: URLStatus):
        url_id = {
            URLStatus.WAITING: self.value.cursor_waiting,
            URLStatus.COMPLETED: self.value.cursor_completed,
            URLStatus.FAILED: self.value.cursor_failed,
        }[url_status]

        if url_id is None:
            return None

        return self.fetch_url(url_id)

    def iter_urls(self, urls_to_iter: URLStatus):
        assert not self.disabled
        while True:
            url = self.fetch_url_at_cursor(urls_to_iter)

            if not url:
                yield None
                continue

            self.value = self.value.copy_with(
                last_scrapet=timestamp(),
                cursor=url.value.next,
                url_status=urls_to_iter,
            )

            yield url

            assert not self.disabled

            url = self.fetch_url(url.key.id, should_raise=False)

            pipe = self.r.pipeline()

            pipe.delete(str(self.key))

            self.key = self.update_key()

            pipe.set(
                str(self.key),
                self.value.to_json(),
            )

            if url:
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

    def append_urls(self, urls: list[URL], url_status: URLStatus):
        # TODO: refactor this please

        assert not self.disabled
        assert len(urls) == len(list(dict.fromkeys([url.value.url for url in urls])))

        pipe = self.r.pipeline()
        for url in urls:
            assert url.key.domain == self.key.domain

            pipe.get(str(url.key))

        results = pipe.execute()

        unique_urls = [u for u, r in zip(urls, results) if not r]

        if len(unique_urls) == 0:
            print("WARNING: appended no unique urls. Ignoring")
            return

        url_at_cursor = self.fetch_url_at_cursor(url_status)
        if url_at_cursor is None:
            urls_to_insert = []

            for i, url in enumerate(unique_urls):
                urls_to_insert.append(
                    url.copy_with(
                        value=url.value.copy_with(
                            prev_id=unique_urls[(i - 1) % len(unique_urls)].key.id,
                            next_id=unique_urls[(i + 1) % len(unique_urls)].key.id,
                        ),
                    ),
                )

            self.value = self.value.copy_with(
                cursor=urls_to_insert[0].key.id,
                url_status=url_status,
            )

            pipe = self.r.pipeline()

            for url in urls_to_insert:
                pipe.set(
                    str(url.key),
                    url.value.to_json(),
                )

            pipe.set(
                str(self.key),
                self.value.to_json(),
            )

            pipe.execute()

            return

        prev_url_id = url_at_cursor.value.prev
        prev_url = self.fetch_url(prev_url_id)

        all_urls = [prev_url, *unique_urls, url_at_cursor]

        urls_to_insert = []

        for url, prev_url, next_url in zip(unique_urls, all_urls[:-2], all_urls[2:]):
            urls_to_insert.append(
                url.copy_with(
                    value=url.value.copy_with(
                        prev_id=prev_url.key.id,
                        next_id=next_url.key.id,
                    ),
                ),
            )

        self.value = self.value.copy_with(
            cursor=urls_to_insert[0].key.id,
            url_status=url_status,
        )

        pipe = self.r.pipeline()

        pipe.set(
            str(prev_url.key),
            prev_url.value.copy_with(next_id=urls_to_insert[0].key.id).to_json(),
        )

        pipe.set(
            str(url_at_cursor.key),
            url_at_cursor.value.copy_with(prev_id=urls_to_insert[-1].key.id).to_json(),
        )

        for url in urls_to_insert:
            pipe.set(
                str(url.key),
                url.value.to_json(),
            )

        pipe.set(
            str(self.key),
            self.value.to_json(),
        )

        pipe.execute()

    def append_url(self, url: URL, url_status: URLStatus):
        return self.append_urls([url], url_status)

    def delete_url(self, url: URL, url_status: URLStatus):
        if url.value.prev == url.value.next:
            if url.key.id == url.value.prev:
                self.r.delete(str(url.key))
                self.value = self.value.with_cursor_none(url_status)
                return

            prev_url = self.fetch_url(url.value.prev)
            prev_url = prev_url.copy_with(
                value=prev_url.value.copy_with(
                    prev_id=prev_url.key.id,
                    next_id=prev_url.key.id,
                ),
            )

            pipe = self.r.pipeline()

            pipe.delete(str(url.key))
            pipe.set(str(prev_url.key), prev_url.value.to_json())

            pipe.execute()

            return

        prev_url, next_url = self.fetch_urls([url.value.prev, url.value.next])

        prev_url = prev_url.copy_with(
            value=prev_url.value.copy_with(next_id=next_url.key.id),
        )

        next_url = next_url.copy_with(
            value=next_url.value.copy_with(prev_id=prev_url.key.id)
        )

        pipe = self.r.pipeline()

        pipe.delete(str(url.key))
        pipe.set(str(prev_url.key), prev_url.value.to_json())
        pipe.set(str(next_url.key), next_url.value.to_json())

        pipe.execute()

        # TODO: don't execute the pipe. Execute both delete and append
        # TODO: at the same time.

    def complete_url(self, url: URL, url_status: URLStatus):
        self.delete_url(self.fetch_url(url.key.id), url_status)
        self.append_url(url, url_status=URLStatus.COMPLETED)

    def fail_url(self, url: URL, url_status: URLStatus):
        self.delete_url(self.fetch_url(url.key.id), url_status)
        self.append_url(url, url_status=URLStatus.FAILED)
