# python -m unittest tests.test_crawler

from time import sleep
import unittest

from redis import Redis

from src.services.prisma_service import clear_tables
from tests.test_website.graph import build_endpoints_graph
from src.models.provisioner import ProvisionerKey, ProvisionerStatus, ProvisionerValue
from src.models.url import URL
from src.services.web_page_service import WebPageService
from src.services.provisioner import Provisioner


class TestCrawler(unittest.TestCase):
    def test_crawler(self):
        with Provisioner() as p:
            with WebPageService.from_domain(p.key.domain) as web:
                for url in p.iter_urls():
                    print(url)

                    if url.visited:
                        break

                    new_urls_str = web.handle_url(url.value.url)
                    new_urls = [URL.from_string(u, p.key.domain) for u in new_urls_str]

                    p.append_urls(new_urls)

                    p.set_scraped(url)

                    sleep(1)

                all_urls = [*p.all_urls()]
                website_graph = build_endpoints_graph()
                nodes = website_graph.nodes
                website_endpoints = [n for n in nodes if "http" not in n]

                self.assertEqual(len(all_urls), len(website_endpoints))

        input("press enter to continue")

    def setUp(self) -> None:
        clear_tables()

        with Redis() as r:
            pipe = r.pipeline()

            for key in r.scan_iter():
                pipe.delete(key)

            domain = "127.0.0.1"

            url = URL.from_string(f"http://{domain}/home", domain)

            pipe.set(str(url.key), url.value.to_json())

            provisioner_key = ProvisionerKey(
                domain=domain,
                status=ProvisionerStatus.OFF,
            )

            provisioner_value = ProvisionerValue(cursor=url.key.id)

            pipe.set(str(provisioner_key), provisioner_value.to_json())

            pipe.execute()

    def tearDown(self) -> None:
        clear_tables()

        with Redis() as r:
            pipe = r.pipeline()

            for key in r.scan_iter():
                pipe.delete(key)

            pipe.execute()


if __name__ == "__main__":
    unittest.main()
