import json
from datetime import datetime, timedelta
from math import floor
from time import sleep
from uuid import uuid4

import loaders
from redis import Redis
from thread import concurrent_threads


class CouldNotFindProvisioner(Exception):
    pass


class AlreadyClaimed(CouldNotFindProvisioner):
    pass


class AlreadyClosed(Exception):
    pass


class TakeOver(Exception):
    pass


def populate_test():
    r = Redis()
    pipe = r.pipeline()

    domain = "example.com"

    provisioner_data = {
        "current": "000",
        "last_scrapet": None,
    }

    for key in r.scan_iter():
        pipe.delete(key)

    pipe.set(f"provisioner:off:{domain}", json.dumps(provisioner_data))

    for i in range(100):
        url_id = f"{i:03d}"
        next_id = (i + 1) % 100
        next_id = f"{next_id:03d}"
        prev_id = (i - 1) % 100
        prev_id = f"{prev_id:03d}"
        data = {
            "url": f"https://www.{domain}/{url_id}",
            "scrapet_at": None,
            "next": next_id,
            "prev": prev_id,
        }
        pipe.set(f"url:{domain}:{url_id}", json.dumps(data))

    pipe.execute()
    r.close()


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

        value = self.r.get(self.key)

        if not value:
            print("Warning: Already Closed")
            return

        new_key = f"provisioner:off:{self.domain()}"
        pipe.set(new_key, value)
        pipe.delete(self.key)

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

    def update_key(self, old_key: str = None):
        key = old_key or self.key
        return f"provisioner:on:{self.time_id()}:{self.id}:{self.domain(key)}"

    def domain(self, key: str = None):
        k = key or self.key
        return k.split(":")[-1]

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

    def claim_provisioner(self, key: str):
        pipe = self.r.pipeline()

        provisioner = self.r.get(key)

        if not provisioner:
            raise AlreadyClaimed(
                "Could not find provisioner. Key was probably modified by another worker"
            )

        provisioner_json = json.loads(provisioner)

        last_scrapet = provisioner_json["last_scrapet"]
        if last_scrapet:
            age = self.timestamp() - last_scrapet
            age_timedelta = timedelta(milliseconds=age)
            print(f"claiming provisioner with age {age_timedelta}")

            old = age_timedelta < self.timeout

            if "on" in key.split(":") and old:
                raise AlreadyClaimed(f"Last scraped was only {age_timedelta} ago")

        new_key = self.update_key(key)
        pipe.set(new_key, provisioner)
        pipe.delete(key)

        _, del_count = pipe.execute()

        if del_count == 0:
            self.r.delete(new_key)
            raise AlreadyClaimed(
                "Could not modify key. Key was probably modified by another worker"
            )

        return new_key, provisioner_json

    def iter_urls(self):
        while True:
            pipe = self.r.pipeline()

            url_key = f"url:{self.domain()}:{self.value['current']}"
            url_json = json.loads(self.r.get(url_key))

            yield url_key, url_json

            now = self.timestamp()

            next_url_id = url_json["next"]

            pipe.delete(self.key)

            self.key = self.update_key()
            self.value = {"current": next_url_id, "last_scrapet": now}
            pipe.set(
                self.key,
                json.dumps(self.value),
            )

            pipe.set(
                url_key,
                json.dumps({**url_json, "scrapet_at": now}),
            )

            result = pipe.execute()
            del_count = result[0]
            if del_count == 0:
                self.r.delete(self.key)
                raise TakeOver(
                    "Could not modify key. Provisioner was probably claimed by another worker"
                )

    def append_url(url: str):
        url_id = hash(url)


def run():
    while True:
        try:
            with Provisioner() as p:
                for url in p.iter_urls():
                    print(url)
                    loader = loaders.ProgressLoader(total=50)
                    for i in range(50):
                        loader.progress(i)
                        sleep(0.01)
                    print()

        except CouldNotFindProvisioner as e:
            print(f"{type(e).__name__} {e}: sleeping...")
            sleep(10)

        except TakeOver:
            print("Warning: TakeOver")
            continue


if __name__ == "__main__":
    # populate_test()
    concurrent_threads(run, thread_count=1)
    # run()
