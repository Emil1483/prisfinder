# python -m unittest tests.test_provisioner

from time import sleep
import unittest

from redis import Redis

from src.services.web_page_service import URLHandler, WebPageService
from src.services.provisioner import Provisioner
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue
from src.models.url import URL


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


class TestProvisioner(unittest.TestCase):
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
                print(url)

        input("press enter to continue")

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

        input("press enter to continue")

    def setUp(self) -> None:
        with Redis() as r:
            pipe = r.pipeline()

            for key in r.scan_iter():
                pipe.delete(key)

            domain = "test.com"

            url = URL.from_string(f"https://www.{domain}", domain)

            pipe.set(str(url.key), url.value.to_json())

            provisioner_key = ProvisionerKey(
                domain=domain,
                status=ProvisionerStatus.OFF,
            )

            provisioner_value = ProvisionerValue(cursor=url.key.id)

            pipe.set(str(provisioner_key), provisioner_value.to_json())

            pipe.execute()

    def tearDown(self) -> None:
        with Redis() as r:
            pipe = r.pipeline()

            for key in r.scan_iter():
                pipe.delete(key)

            pipe.execute()


if __name__ == "__main__":
    unittest.main()
