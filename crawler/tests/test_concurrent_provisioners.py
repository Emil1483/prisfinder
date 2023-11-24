# python -m unittest tests.test_concurrent_provisioners

import multiprocessing
from time import sleep
import unittest
from src.models.provisioner import ProvisionerStatus

from src.services.provisioner import (
    Provisioner,
    all_provisioner_keys,
    push_provisioner,
    clear_provisioners,
)


def run(start_event, stop_event):
    with Provisioner() as p:
        start_event.set()
        for _ in p.iter_urls():
            sleep(0.1)
            if stop_event.is_set():
                break


class TestConcurrentProvisioner(unittest.TestCase):
    def add_provisioner(self, wait=False):
        start_event = multiprocessing.Event()
        stop_event = multiprocessing.Event()
        provisioner = multiprocessing.Process(
            target=run, args=(start_event, stop_event)
        )
        provisioner.start()
        self.provisioners.append((provisioner, start_event, stop_event))

        if wait:
            start_event.wait()

    def stop(self, i):
        provisioner, _, stop_event = self.provisioners[i]
        stop_event.set()
        provisioner.join()
        self.provisioners.pop(i)

    def restart(self, i, wait=False):
        provisioner, start_event, stop_event = self.provisioners[i]
        stop_event.set()
        provisioner.join()
        start_event.clear()
        stop_event.clear()
        provisioner = multiprocessing.Process(
            target=run, args=(start_event, stop_event)
        )
        provisioner.start()

        if wait:
            start_event.wait()

    def wait_for(self, *provisioners):
        start_events = [self.provisioners[i][1] for i in provisioners]
        for start_event in start_events:
            if not start_event.is_set():
                start_event.wait()

    def test_prioritization(self):
        def expect(truth_table: dict):
            truth_table_copy = truth_table.copy()
            for key in all_provisioner_keys():
                domain, status = key.domain, key.status
                if domain in truth_table:
                    self.assertEqual(truth_table[domain], status)
                    del truth_table_copy[domain]

            self.assertEqual(len(truth_table_copy), 0)

        on = ProvisionerStatus.ON
        off = ProvisionerStatus.OFF

        for i in range(5):
            self.add_provisioner(wait=True)
            expect(
                {
                    "priority0.com": on if i >= 0 else off,
                    "priority1.com": on if i >= 1 else off,
                    "priority2.com": on if i >= 2 else off,
                    "priority3.com": on if i >= 3 else off,
                    "priority4.com": on if i >= 4 else off,
                }
            )

        self.stop(0)
        self.restart(3, wait=True)
        expect(
            {
                "priority0.com": on,
                "priority1.com": on,
                "priority2.com": on,
                "priority3.com": on,
                "priority4.com": off,
            }
        )

        self.stop(1)
        self.restart(1, wait=True)

        expect(
            {
                "priority0.com": on,
                "priority1.com": on,
                "priority2.com": on,
                "priority3.com": off,
                "priority4.com": off,
            }
        )

        self.add_provisioner(wait=True)

        expect(
            {
                "priority0.com": on,
                "priority1.com": on,
                "priority2.com": on,
                "priority3.com": on,
                "priority4.com": off,
            }
        )

        for _ in range(len(self.provisioners)):
            self.stop(0)

        sleep(1)

    def setUp(self) -> None:
        self.provisioners = []

        clear_provisioners()
        push_provisioner("http://www.priority1.com/", priority=1)
        push_provisioner("http://www.priority4.com/", priority=4)
        push_provisioner("http://www.priority3.com/", priority=3)
        push_provisioner("http://www.priority0.com/", priority=0)
        push_provisioner("http://www.priority2.com/", priority=2)

    def tearDown(self) -> None:
        clear_provisioners()
