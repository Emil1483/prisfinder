import importlib
from pathlib import Path
from typing import Callable


def import_module(function_path: str):
    src_dir = Path(__file__).parent.parent
    module_path = str(src_dir.joinpath(function_path))

    loader = importlib.machinery.SourceFileLoader(function_path, module_path)
    spec = importlib.util.spec_from_loader(function_path, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    return module


def import_scraper(domain: str) -> Callable:
    try:
        module = import_module(f"scrapers/{domain}.py")

        function = getattr(module, "scrape")
        return function
    except FileNotFoundError:
        return None
