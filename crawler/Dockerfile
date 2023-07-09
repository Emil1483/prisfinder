FROM mcr.microsoft.com/playwright/python:v1.35.0-jammy

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENV PYTHONPATH "${PYTHONPATH}:/app"


CMD ["python", "-u", "scripts/worker.py"]