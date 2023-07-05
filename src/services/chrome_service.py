from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


class ChromeService:
    def __enter__(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

        self._driver = webdriver.Chrome(options)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._driver.quit()

    def get(self, url: str):
        try:
            return self._driver.get(url)
        except Exception as e:
            print("WARNING", type(e), type(e).__name__, e)
            self._driver.quit()
            self.__enter__()
            return self.get(url)

    @property
    def page_source(self):
        return self._driver.page_source

    @property
    def current_url(self):
        return self._driver.current_url
