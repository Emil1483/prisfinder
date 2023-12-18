# python -m unittest tests.test_api

from multiprocessing import Event, Process, Queue
from time import sleep
import unittest

from scripts.api import app
from scripts.worker import run

from src.services.provisioner import (
    CouldNotFindProvisioner,
    ExitProvisioner,
    Provisioner,
    TakeOver,
)
from src.services.redis_service import RedisService
from src.models.provisioner import ProvisionerStatus
from src.models.product import Product, Retailer
from src.services.prisma_service import clear_tables, get_product_by_id, upsert_product


def test_handler(p: Provisioner, start_event: Event = None):
    if start_event:
        start_event.set()

    for url in p.iter_urls():
        print(url)
        sleep(0.1)


def test_worker():
    run(test_handler)


def async_test_worker(q: Queue, start_event: Event):
    try:
        run(test_handler, start_event=start_event)

    except Exception as e:
        q.put(e)


def async_worker(q: Queue, start_event: Event):
    try:
        run(start_event=start_event)

    except Exception as e:
        q.put(e)


class TestAPI(unittest.TestCase):
    def start_worker(self, target):
        start_event = Event()
        self.q = Queue()

        self.provisioner = Process(target=target, args=(self.q, start_event))
        self.provisioner.start()

        while True:
            if start_event.is_set():
                break

            if not self.q.empty():
                raise self.q.get()

            sleep(0.1)

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        with RedisService() as r:
            r.clear_provisioners()

            self.product_ids = []
            for i in range(5):
                self.product_ids.append(
                    upsert_product(
                        Product(
                            name=f"product {i}",
                            description="description",
                            brand="brand",
                            gtins=[f"{i}"],
                            mpns=[f"mpn {i}"],
                            image=f"image_{i}.jpg",
                            retailers=[
                                Retailer(
                                    category="general",
                                    name="Elkjop",
                                    price=399.99,
                                    url=f"https://www.elkjop.no/{i}",
                                    sku=f"sku-{i}",
                                ),
                            ],
                        )
                    )
                )

    def tearDown(self) -> None:
        clear_tables()
        with RedisService() as r:
            r.clear_provisioners()

    def test_setting_finn_query(self):
        with RedisService() as r:
            r.insert_provisioner("", priority=0, domain="finn.no")

            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.off)

            self.assertRaises(ExitProvisioner, run)

            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.disabled)

            # TODO: use dependency injection to mock the finn service

            response = self.client.patch(
                f"/products/{self.product_ids[0]}",
                json={"finn_query": "Garmin Forerunner 225"},
            )

            self.assertEqual(response.status_code, 200, response.text)

            response = self.client.patch(
                f"/products/{self.product_ids[1]}",
                json={"finn_query": "Garmin Forerunner 245"},
            )

            self.assertEqual(response.status_code, 200, response.text)

            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.off)

            self.start_worker(async_worker)

            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.on)

            response = self.client.patch(
                f"/products/{self.product_ids[2]}",
                json={"finn_query": "Galaxy Buds2 Pro"},
            )

            self.assertEqual(response.status_code, 200, response.text)

            response = self.client.patch(
                f"/products/{self.product_ids[3]}",
                json={"finn_query": "Samsung Case"},
            )

            self.assertEqual(response.status_code, 200, response.text)

            response = self.client.patch(
                f"/products/{self.product_ids[4]}",
                json={"finn_query": "Galaxy buds live"},
            )

            self.assertEqual(response.status_code, 200, response.text)

            exception = self.q.get(block=True, timeout=10)

            self.assertEqual(type(exception), ExitProvisioner)

            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.disabled)

            for product_id in self.product_ids:
                product = get_product_by_id(product_id)
                self.assertGreater(len(product.finn_ads), 0)

    def test_disable_enable_provisioner(self):
        with RedisService() as r:
            r.insert_provisioner("http://www.test.com/", priority=0)

        self.start_worker(async_test_worker)

        response = self.client.post("/provisioners/test.com/disable")
        self.assertEqual(response.status_code, 200, response.text)

        exception = self.q.get(block=True, timeout=10)
        self.assertIsInstance(exception, TakeOver)

        self.assertRaises(CouldNotFindProvisioner, test_worker)

        response = self.client.post("/provisioners/test.com/enable")
        self.assertEqual(response.status_code, 200, response.text)

        self.start_worker(async_test_worker)

        response = self.client.post("/provisioners/test.com/disable")
        self.assertEqual(response.status_code, 200, response.text)

        exception = self.q.get(block=True, timeout=10)
        self.assertIsInstance(exception, TakeOver)


if __name__ == "__main__":
    unittest.main()
