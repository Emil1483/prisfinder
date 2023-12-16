# python -m unittest tests.test_crawler

from time import sleep
import unittest

from src.services.prisma_service import clear_tables
from src.services.redis_service import RedisService
from tests.test_website.graph import build_endpoints_graph
from src.models.url import URL
from src.services.web_page_service import WebPageService
from src.services.provisioner import Provisioner


class TestCrawler(unittest.TestCase):
    def test_crawler(self):
        # TODO use worker.py
        with Provisioner() as p:
            with WebPageService.from_domain(self.domain) as web:
                for url in p.iter_urls():
                    print(url)

                    if url.visited:
                        break

                    new_urls_str = web.handle_url(url.value.url)
                    # sleep(10)

                    new_urls = [URL.from_string(u, self.domain) for u in new_urls_str]

                    p.append_urls(new_urls)

                    p.set_scraped(url)

                all_urls = [*p.all_urls()]
                website_graph = build_endpoints_graph()
                nodes = website_graph.nodes
                website_endpoints = [n for n in nodes if "http" not in n]

                self.assertEqual(len(all_urls), len(website_endpoints))

    def setUp(self) -> None:
        with RedisService() as r:
            clear_tables()

            r.clear_provisioners()

            self.domain = "127.0.0.1"
            r.push_provisioner(f"http://{self.domain}/home", priority=1)

    def tearDown(self) -> None:
        with RedisService() as r:
            clear_tables()
            r.clear_provisioners()


if __name__ == "__main__":
    unittest.main()
