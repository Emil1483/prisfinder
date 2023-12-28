import typer
from crawler.src.services.prisma_service import clear_tables

from src.models.url import FailedURLKey
from src.services.redis_service import RedisService

app = typer.Typer()


@app.command()
def download(REDIS_URL: str = typer.Option(..., "-f", "--from")):
    print(f'downloading from "{REDIS_URL}"')
    i = 0

    with RedisService.from_env_url() as home:
        other_service: RedisService = RedisService.from_url(REDIS_URL)
        with other_service as other:
            home.clear_provisioners()
            for raw_key in other.scan_provisioner_keys():
                p_key, p_value = other.fetch_provisioner(raw_key.domain)
                home.set(str(p_key), p_value.to_json())

                for url_key, url_value in other.iter_urls(p_key.domain, p_value.cursor):
                    home.set(str(url_key), url_value.to_json())

                    if url_value.failed_at:
                        failed_url_key = FailedURLKey.from_url_key(url_key)
                        home.set(str(failed_url_key), b"")

                    i += 1
                    print(i)


@app.command()
def upload(REDIS_URL: str = typer.Option(..., "-t", "--to")):
    print(f'uploading to "{REDIS_URL}"')
    i = 0
    with RedisService.from_env_url() as home:
        other_service: RedisService = RedisService.from_url(REDIS_URL)
        with other_service as other:
            other.clear_provisioners()
            for raw_key in home.scan_provisioner_keys():
                p_key, p_value = home.fetch_provisioner(raw_key.domain)
                other.set(str(p_key), p_value.to_json())

                for url_key, url_value in home.iter_urls(p_key.domain, p_value.cursor):
                    other.set(str(url_key), url_value.to_json())

                    if url_value.failed_at:
                        failed_url_key = FailedURLKey.from_url_key(url_key)
                        other.set(str(failed_url_key), b"")

                    i += 1
                    print(i)


if __name__ == "__main__":
    app()
