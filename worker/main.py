import json
from datetime import datetime
from time import sleep

from redis import Redis


class AlreadyClaimed(Exception):
    pass


class AlreadyClosed(Exception):
    pass


def populate_test():
    r = Redis(host="localhost", port=6379)
    pipe = r.pipeline()

    domain = "example.com"

    provisioner_data = {
        "current": "000",
        "last_scrapet": None,
    }

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
        r.set(f"url:{domain}:{url_id}", json.dumps(data))

    pipe.execute()
    r.close()


class Provisioner(Redis):
    def __str__(self) -> str:
        return f"(key: {self.key}, value: {self.value})"

    def claim_provisioner(self, key: str):
        pipe = self.pipeline()

        provisioner = self.get(key)

        if not provisioner:
            raise AlreadyClaimed()

        domain = key.split(":")[-1]

        new_key = f"provisioner:on:{domain}"
        pipe.set(new_key, provisioner)
        pipe.delete(key)

        _, del_count = pipe.execute()

        if del_count == 0:
            raise AlreadyClaimed()

        return new_key, json.loads(provisioner)

    def find_provisioner(self):
        # TODO: treat stale provisioners as off
        while True:
            for provisioner_key in self.scan_iter("provisioner:off:*"):
                try:
                    key = provisioner_key.decode()
                    return self.claim_provisioner(key)
                except AlreadyClaimed:
                    continue

            print("sleeping...")
            sleep(10)

    def __enter__(self):
        self.key, self.value = self.find_provisioner()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pipe = self.pipeline()

        value = self.get(self.key)

        if not value:
            raise AlreadyClosed()

        new_key = f"provisioner:off:{self.domain}"
        pipe.set(new_key, value)
        pipe.delete(self.key)

        _, del_count = pipe.execute()

        if del_count == 0:
            raise AlreadyClosed()

    @property
    def domain(self):
        return self.key.split(":")[-1]

    def fetch_current_url(self):
        key = f"url:{self.domain}:{self.value['current']}"
        url_json = self.get(key)
        return key, json.loads(url_json)

    def iter_urls(self):
        while True:
            pipe = self.pipeline()

            current_url_key, current_url = self.fetch_current_url()
            yield current_url_key, current_url

            now = round(datetime.now().timestamp() * 1000)

            next_url_id = current_url["next"]
            self.value = {"current": next_url_id, "last_scrapet": now}
            pipe.set(
                self.key,
                json.dumps(self.value),
            )

            pipe.set(
                current_url_key,
                json.dumps({**current_url, "scrapet_at": now}),
            )

            pipe.execute()


def run():
    with Provisioner() as p:
        print(p)
        for url in p.iter_urls():
            print(url)
            sleep(0.5)


if __name__ == "__main__":
    # populate_test()
    run()
