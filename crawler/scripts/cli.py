import os
import re
from string import printable
from urllib.parse import urlparse
import typer

from src.models.url import FailedURLKey
from src.services.redis_service import RedisService
from src.services.prisma_service import prisma, clear_tables
from prisma.errors import RawQueryError
import re

app = typer.Typer()


@app.command()
def download_redis(REDIS_URL: str = typer.Option(..., "-f", "--from")):
    print(f'downloading from "{REDIS_URL}"')

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


@app.command()
def upload_redis(REDIS_URL: str = typer.Option(..., "-t", "--to")):
    print(f'uploading to "{REDIS_URL}"')
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


@app.command()
def download_sql_dump(POSTGRESQL_URL: str = typer.Option(..., "-f", "--from")):
    print(f'downloading from "{POSTGRESQL_URL}"')

    parsed_url = urlparse(POSTGRESQL_URL)
    host = parsed_url.hostname
    user = parsed_url.username
    password = parsed_url.password
    database = parsed_url.path.lstrip("/")

    os.environ["PGPASSWORD"] = password
    os.system(
        f"pg_dump --column-inserts --attribute-inserts -U {user} -h {host} {database} > backup/backup.sql"
    )


@app.command()
def install_sql_dump():
    with open("backup/backup.sql") as f:
        print("executing sql dump from backup.sql")

        def execute(ranges: list):
            failed_ranges = []
            for _, start, end in ranges:
                f.seek(start)
                current = ""
                char_pos = start
                while char_pos < end:
                    line = f.readline()
                    char_pos += len(line) + 1

                    if not line:
                        break

                    sql = re.sub("[^{}]+".format(printable), "", line)
                    sql = re.sub("(\r\n|\n|\r)", "", sql)
                    sql = re.sub("\s+", " ", sql)

                    if not sql or sql.startswith("--"):
                        continue

                    current += sql

                    if sql.endswith(";") and "INSERT" in current:
                        try:
                            prisma.execute_raw(current)
                        except RawQueryError as e:
                            if not failed_ranges:
                                failed_ranges.append(
                                    (str(e), char_pos - len(line) - 1, char_pos)
                                )

                            elif failed_ranges[-1][0] == str(e):
                                failed_ranges[-1] = (
                                    failed_ranges[-1][0],
                                    failed_ranges[-1][1],
                                    char_pos,
                                )

                            else:
                                failed_ranges.append(
                                    (str(e), char_pos - len(line) - 1, char_pos)
                                )
                        finally:
                            current = ""

            return failed_ranges

        clear_tables()
        ranges = [(None, 0, float("inf"))]
        for _ in range(3):
            ranges = execute(ranges)

        for e, _, _ in ranges:
            print("WARNING:", e, type(e))


@app.command()
def download_and_install_sql(POSTGRESQL_URL: str = typer.Option(..., "-f", "--from")):
    download_sql_dump(POSTGRESQL_URL)
    install_sql_dump()


if __name__ == "__main__":
    app()
