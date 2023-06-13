import hashlib
import json
from datetime import datetime, timedelta
from math import floor
from uuid import uuid4

from redis import Redis

from worker.src.models.provisioner import ProvisionerKey, ProvisionerValue
from worker.src.models.url import URL, URLKey, URLValue


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
        self.r = Redis()
        self.id = uuid4().hex

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

        new_key = self.key.turn_off()
        pipe.set(str(new_key), value)
        pipe.delete(str(self.key))

        _, del_count = pipe.execute()

        if del_count == 0:
            raise AlreadyClosed()

        self.r.quit()

    def timestamp(self):
        return round(datetime.now().timestamp() * 1000)

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
            on=True,
            provisioner_id=self.id,
            time_id=self.time_id(),
        )

    def find_provisioner(self):
        print([*self.r.scan_iter("provisioner:*")])

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

    def claim_provisioner(self, key_str: str):
        pipe = self.r.pipeline()

        provisioner = self.r.get(key_str)

        if not provisioner:
            raise AlreadyClaimed(
                "Could not find provisioner. Key was probably modified by another worker"
            )

        provisioner_json = json.loads(provisioner)

        value: ProvisionerValue = ProvisionerValue.from_dict(provisioner_json)

        if value.last_scrapet:
            age = self.timestamp() - value.last_scrapet
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

    def iter_urls(self):
        while True:
            pipe = self.r.pipeline()

            url_key = URLKey(
                domain=self.key.domain,
                id=self.value.current,
            )

            url = URL(
                key=url_key,
                value=URLValue.from_json(self.r.get(str(url_key))),
            )

            yield url

            now = self.timestamp()

            pipe.delete(str(self.key))

            self.key = self.update_key()
            self.value = ProvisionerValue(current=url.value.next, last_scrapet=now)
            pipe.set(
                str(self.key),
                self.value.to_json(),
            )

            pipe.set(
                str(url.key),
                url.value.copy_with(scrapet_at=now).to_json(),
            )

            result = pipe.execute()
            del_count = result[0]
            if del_count == 0:
                self.r.delete(str(self.key))
                raise TakeOver(
                    "Could not modify key. Provisioner was probably claimed by another worker"
                )

    def append_url(url: str):
        string_bytes = url.encode(encoding="utf8")
        hexdigest = hashlib.sha256(string_bytes).hexdigest()
        url_id = hexdigest[:32]
