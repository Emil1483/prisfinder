from multiprocessing import Manager, Pool
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


def execute(args):
    failed, sql = args
    try:
        print(sql)
        prisma.execute_raw(sql)
    except RawQueryError:
        failed.append(sql)


@app.command()
def install_sql_dump():
    with open("backup/backup.sql") as f:
        print("executing sql dump from backup.sql")

        index = {}
        char_pos = 0
        sql = ""
        for line in f:
            start = char_pos
            end = start + len(line)
            char_pos = end + 1

            current = re.sub("[^{}]+".format(printable), "", line)
            current = re.sub("(\r\n|\n|\r)", "", current)
            current = re.sub("\s+", " ", current)

            if not current or current.startswith("--"):
                continue

            sql += current

            if sql.endswith(";"):
                if "INSERT" not in sql:
                    continue

                table = sql.split('"')[1]
                sql = ""

                if table not in index:
                    index[table] = start, end
                else:
                    index[table] = index[table][0], end

        def generate_sql(start, end):
            f.seek(start)
            sql = ""
            chars_left = end - start
            while chars_left > 0:
                line = f.readline()
                chars_left -= len(line) + 1

                current = re.sub("[^{}]+".format(printable), "", line)
                current = re.sub("(\r\n|\n|\r)", "", current)
                current = re.sub("\s+", " ", current)

                if not current or current.startswith("--"):
                    continue

                sql += current

                if sql.endswith(";"):
                    yield sql
                    sql = ""

        clear_tables()

        def process_sqls(sqls, manager: Manager, pool: Pool):
            failed = manager.list()
            gen = ((failed, sql) for sql in sqls)
            pool.map(execute, gen)
            return [*failed]

        with Manager() as manager, Pool(processes=10) as pool:
            failed = process_sqls(generate_sql(*index["Product"]), manager, pool)
            failed = process_sqls(failed, manager, pool)
            assert not failed

            failed = process_sqls(generate_sql(*index["FinnAd"]), manager, pool)
            assert not failed

            failed = process_sqls(generate_sql(*index["Gtin"]), manager, pool)
            assert not failed

            failed = process_sqls(generate_sql(*index["Mpn"]), manager, pool)
            assert not failed

            failed = process_sqls(
                generate_sql(*index["ProductRetailer"]), manager, pool
            )
            assert not failed


@app.command()
def download_and_install_sql(POSTGRESQL_URL: str = typer.Option(..., "-f", "--from")):
    download_sql_dump(POSTGRESQL_URL)
    install_sql_dump()


if __name__ == "__main__":
    app()
