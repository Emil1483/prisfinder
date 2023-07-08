FROM python:3.10-slim


WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN playwright install webkit

COPY . .

ENV PYTHONPATH "${PYTHONPATH}:/app"


CMD ["python", "-u", "scripts/worker.py"]