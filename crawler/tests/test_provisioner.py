# python -m unittest tests.test_provisioner

from datetime import timedelta
from multiprocessing import Event, Process, Queue
from time import sleep, time
import unittest
import os

os.environ[
    "POSTGRESQL_URL"
] = "postgresql://test:rootpassword@localhost:5433/prisfinder"

os.environ["REDIS_URL"] = "redis://localhost:6379"

from scripts.worker import run
from src.services.prisma_service import (
    clear_tables,
    count_pending_urls,
    insert_pending_urls,
)
from src.services.redis_service import RedisService
from src.services.web_page_service import URLHandler, WebPageService
from src.models.url import URL
from src.services.provisioner import (
    ExitProvisioner,
    Provisioner,
    ProvisionerTooOld,
)


class TestURLHandler(URLHandler):
    def handle_url(self, url: str) -> list[str]:
        if url == "https://www.test.com":
            return [
                "https://www.test.com/p/0",
                "https://www.test.com/p/1",
                "https://www.test.com/p/2",
            ]

        if url == "https://www.test.com/p/0":
            return ["https://www.abc.xyz/"]

        if url == "https://www.test.com/p/1":
            return ["https://www.test.com/p/1/0"]

        if url == "https://www.test.com/p/2":
            return [
                "https://www.test.com",
                "https://www.test.com/p/2/0",
                "https://www.test.com/p/2/1",
            ]

        return []

    def setup(self):
        pass

    def teardown(self):
        pass


class InfiniteURLHandler(URLHandler):
    def handle_url(self, url: str) -> list[str]:
        sleep(0.1)
        if url == "https://www.test.com":
            return [
                "https://www.test.com/0",
            ]

        i = int(url.split("/")[-1])
        return [f"https://www.test.com/{i + 1}"]

    def setup(self):
        pass

    def teardown(self):
        pass


def async_worker(q: Queue, start_event: Event):
    try:
        run(
            start_event=start_event,
            max_age=timedelta(seconds=5),
            service=WebPageService(InfiniteURLHandler()),
        )

    except Exception as e:
        q.put(e)


class TestProvisioner(unittest.TestCase):
    def test_provisioner_too_old(self):
        exceptions = Queue()
        start_event = Event()

        p = Process(target=async_worker, args=(exceptions, start_event))
        p.start()

        start_event.wait()

        start = time()

        exception = exceptions.get()

        end = time()

        self.assertIsInstance(exception, ProvisionerTooOld)
        self.assertAlmostEqual(end - start, 5, delta=0.5)

    def test_pending_urls(self):
        insert_pending_urls(
            self.domain,
            [
                "https://test.com/q/0",
                "https://test.com/q/1",
                "https://test.com/q/2",
                "https://test.com/q/3",
            ],
        )

        visited_urls = {}

        try:
            with Provisioner() as p:
                for url in p.iter_urls():
                    print(url)

                    visited_urls[url.value.url] = True

                    if url.visited:
                        p.append_pending_urls()
                        continue

                    p.set_scraped(url)

        except ExitProvisioner as e:
            print(f"exit provisioner: {e.reason}")

        self.assertEqual(count_pending_urls(self.domain), 0)
        self.assertEqual(len(visited_urls.keys()), 5)

    def test_fail_urls(self):
        with Provisioner() as p:
            p.append_url(
                URL.from_string(
                    "https://www.test.com/fail",
                    domain=p.key.domain,
                ),
            )

            for url in p.all_urls():
                if url.value.url.endswith("fail"):
                    p.fail_url(url)
                else:
                    p.set_scraped(url)

            for url in p.all_urls():
                failed = url.value.failed_at != None
                failed_url = url.value.url.endswith("fail")
                self.assertTrue(failed == failed_url)

            self.assertListEqual(
                ["https://www.test.com/fail"],
                [u.value.url for u in p.all_failed_urls()],
            )

    def test_append_urls(self):
        urls = []
        with Provisioner() as p:
            with WebPageService(TestURLHandler()) as web:
                for url in p.iter_urls():
                    print(url)

                    if url.visited:
                        break

                    urls.append(url.value.url)

                    new_urls_str = web.handle_url(url.value.url)
                    new_urls = [URL.from_string(u, p.key.domain) for u in new_urls_str]

                    p.append_urls(new_urls)

                    p.set_scraped(url)

        self.assertListEqual(
            urls,
            [
                "https://www.test.com",
                "https://www.test.com/p/0",
                "https://www.test.com/p/1",
                "https://www.test.com/p/1/0",
                "https://www.test.com/p/2",
                "https://www.test.com/p/2/0",
                "https://www.test.com/p/2/1",
            ],
        )

    def setUp(self) -> None:
        clear_tables()
        with RedisService.from_env_url() as r:
            r.clear_provisioners()

            self.domain = "test.com"
            r.insert_provisioner(f"https://www.{self.domain}", priority=1)

    def tearDown(self) -> None:
        clear_tables()
        with RedisService.from_env_url() as r:
            r.clear_provisioners()


if __name__ == "__main__":
    unittest.main()
