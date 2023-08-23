from abc import ABC, abstractmethod


class URLHandler(ABC):
    @abstractmethod
    def handle_url(self, url: str) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def setup(self):
        raise NotImplementedError()

    @abstractmethod
    def teardown(self):
        raise NotImplementedError()
