# python -m unittest tests.test_api

from multiprocessing import Event, Process, Queue
from time import sleep
import unittest

from scripts.api import app
from scripts.worker import run as work

from src.services.provisioner import ExitProvisioner
from src.services.redis_service import RedisService
from src.models.provisioner import ProvisionerStatus
from src.models.product import Product, Retailer
from src.services.prisma_service import clear_tables, get_product_by_id, upsert_product


def work_async(q: Queue, start_event: Event):
    try:
        work(start_event)

    except Exception as e:
        q.put(e)


class TestAPI(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

        with RedisService() as r:
            r.clear_provisioners()
            r.push_provisioner("", priority=0, domain="finn.no")

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
            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.off)

            self.assertRaises(ExitProvisioner, work)

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

            start_event = Event()
            q = Queue()
            worker = Process(target=work_async, args=(q, start_event))
            worker.start()

            while True:
                if start_event.is_set():
                    break

                if not q.empty():
                    raise q.get()

                sleep(0.1)

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

            exception = q.get(block=True, timeout=10)

            self.assertEqual(type(exception), ExitProvisioner)

            key, _ = r.fetch_provisioner("finn.no")
            self.assertEqual(key.status, ProvisionerStatus.disabled)

            for product_id in self.product_ids:
                product = get_product_by_id(product_id)
                self.assertGreater(len(product.finn_ads), 0)


if __name__ == "__main__":
    unittest.main()
