import ctypes
import gc
import threading
from threading import Thread
from time import sleep


class StopThread(BaseException):
    pass


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

    def throw(self, error):
        if error is self.exc:
            return

        self.exc = error

        self.kill(error)

    def kill(self, error=None):
        thread_id = self.get_id()
        if not thread_id:
            return

        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread_id), ctypes.py_object(error or SystemExit)
        )

        if ret == 0:
            raise ValueError("Invalid thread ID")

        elif ret > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")


class ContextManager:
    def __enter__(self):
        print("ENTER")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("EXIT")


def concurrent_workers(function, workers_count=5):
    threads: list[MyThread] = []
    for _ in range(workers_count):
        t = MyThread(target=function)
        t.daemon = True
        t.start()

        threads.append(t)

    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                if not t.is_alive():
                    continue

                try:
                    t.join(0.1)
                except BaseException as e:
                    t.kill()
                    raise e

    except BaseException as e:
        for t in threads:
            if t.is_alive():
                t.kill()

        while any(t.is_alive() for t in threads):
            sleep(0.1)

        raise e


if __name__ == "__main__":

    def run():
        with ContextManager():
            i = 0

            while True:
                try:
                    print("count:", i)
                    i += 1
                    sleep(1)

                except Exception as e:
                    print("Exception", e)

                # if random() < 0.1:
                #     break

                # if random() < 0.1:
                #     raise Exception()

    concurrent_workers(run, workers_count=2)
