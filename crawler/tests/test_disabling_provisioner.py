# python -m unittest tests.test_disabling_provisioner

from multiprocessing import Event, Process, Queue
from time import sleep
import unittest
from src.services.provisioner import CouldNotFindProvisioner, Provisioner, TakeOver

from src.services.redis_service import RedisService


def run(q: Queue, start_event: Event):
    try:
        with Provisioner() as p:
            start_event.set()
            for url in p.iter_urls():
                print(url)
                sleep(0.1)

    except Exception as e:
        q.put(e)


class TestDisablingProvisioner(unittest.TestCase):
    def start_provisioner(self):
        start_event = Event()
        self.q = Queue()

        self.provisioner = Process(target=run, args=(self.q, start_event))
        self.provisioner.start()

        while True:
            if start_event.is_set():
                break

            if not self.q.empty():
                raise self.q.get()

            sleep(0.1)

    def setUp(self) -> None:
        with RedisService() as r:
            r.clear_provisioners()
            r.push_provisioner("http://www.test.com/", priority=0)

    def test_disable_enable_provisioner(self):
        with RedisService() as r:
            self.start_provisioner()

            r.disable_provisioner("test.com")

            exception = self.q.get(block=True, timeout=10)
            self.assertIsInstance(exception, TakeOver)

            self.assertRaises(CouldNotFindProvisioner, self.start_provisioner)

            r.enable_provisioner("test.com")

            self.start_provisioner()

            r.disable_provisioner("test.com")
            exception = self.q.get(block=True, timeout=10)
            self.assertIsInstance(exception, TakeOver)

    def tearDown(self) -> None:
        with RedisService() as r:
            r.clear_provisioners()


if __name__ == "__main__":
    unittest.main()
