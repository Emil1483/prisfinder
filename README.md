# Prisfinder

This is a price comparison website - not an unique idea. However, what makes this project worth pursuing is its unique integration with finn.no, providing users with a comprehensive view of both new and second-hand options. The idea bowls down to my theory that, provided the user can compare new and second-hand prices, the user will be more likely to seek the sustainable alternative.

The project currently consists of two parts, the [website](#website) and the [crawler](#crawler). Note that the project is still under development and is expected to release sometime in 2024.

For developing the website and the crawler, we will need a postgres database. And for developing the crawler, we'll need a redis database. For developing locally, we'll use local docker containers for that.

First install [Docker](https://www.docker.com/products/docker-desktop/).

Then, run

```bash
cd crawler
docker compose up -d
```

## Crawler

To get started developing the crawler, make sure you have the following installed:

1. [Python 3.10 or higher](https://www.python.org/downloads/)
2. [Node](https://nodejs.org/en/download)

```Bash
winget install -e --id Python.Python.3.11
winget install -e --id OpenJS.NodeJS
```

Then, create a .env file with a `POSTGRESQL_URL` pointing to the created postgres docker container

```
POSTGRESQL_URL=postgresql://root:rootpassword@localhost:5432/prisfinder
```

Then, run

```Bash
cd crawler

python -m venv venv
./venv/Scripts/Activate.ps1

pip install -r requirements.txt

prisma db push
playwright install
```

Then, add the **full path to the /crawler** directory to your `PYTHONPATH` environment variable. On windows, this can be done by editing the `$profile`. See [this Stackoverflow question](https://stackoverflow.com/questions/714877/setting-windows-powershell-environment-variables):

By now, you should be good to go. Use the following command to run the tests:

```Bash
cd crawler
python -m unittest
```

Note that the test_crawler tests require the test_website to be running. This can be done by running the following in a separate terminal:

```bash
cd crawler
python /tests/test_website/index.py
```

Finally, to start crawling, first push a retailer provisioner with

```Bash
cd crawler
python scripts/push_power.py
```

Then, run the following to start crawling. You may have multiple scripts running concurrently for crawling with multiple provisioners at the same time. Render.com's background worker service works well for this. Note that the project is also dockerized for easy deployment.

```Bash
cd crawler
python scripts/worker.py
```

## Website

The website is currently a simple, bare bones next.js website written in typescript. To develop the website, first install the required dependencies. For windows, run

```bash
winget install -e --id Yarn.Yarn
```

Then, create a .env file with a `POSTGRESQL_URL` pointing to the created postgres docker container

```
POSTGRESQL_URL=postgresql://root:rootpassword@localhost:5432/prisfinder
```

Then, run

```bash
cd website
yarn install
yarn run dev
```
