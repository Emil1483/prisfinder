# Prisfinder

To get started developing the crawler, make sure you have the following installed:

1. [Python 3.10 or higher](https://www.python.org/downloads/)
2. [Node](https://nodejs.org/en/download)
3. [Docker](https://www.docker.com/products/docker-desktop/)

On windows, this can be done with. Note that Docker has to be install manually

```PowerShell
winget install -e --id Python.Python.3.11
winget install -e --id OpenJS.NodeJS
```

Then, setup the docker containers

```Bash
cd crawler
docker compose up -d
```

Then, create a .env file pointing to the created postgres docker container

```
POSTGRESQL_URI=postgresql://root:rootpassword@localhost:5432/prisfinder
```

Then, run

```Bash
cd crawler
pip install venv
python -m venv venv
pip install -r requirements.txt
prisma db push
```

Then, add the **full path to the /crawler** directory to your `PYTHONPATH` variable. On windows, simply run:

```PowerShell
.\setup.ps1
```

By now, you should be good to go. Use the following command to run the tests

```Bash
python -m unittest
```
