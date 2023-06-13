import ctypes
import threading
from threading import Thread


class MyThread(Thread):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.exc = None
        self.ret = None

    def run(self):
        self.exc = None
        self.ret = None
        try:
            if hasattr(self, "_Thread__target"):
                self.ret = self._Thread__target(
                    *self._Thread__args, **self._Thread__kwargs
                )
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        if self.exc:
            raise self.exc
        super(MyThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret

    def get_id(self):
        if hasattr(self, "_thread_id"):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def throw(self, error=None):
        self.exc = error
        thread_id = self.get_id()

        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            thread_id, ctypes.py_object(error or SystemExit)
        )

        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)

        # self._stop()


def concurrent_threads(function, thread_count=5):
    threads: list[MyThread] = []
    for _ in range(thread_count):
        t = MyThread(target=function)
        t.daemon = True
        t.start()

        threads.append(t)

    while any(t.is_alive() for t in threads):
        if t in threads:
            if not t.is_alive():
                continue

            try:
                t.join(0.1)
            except BaseException as e:
                t.throw(e)
                raise e
