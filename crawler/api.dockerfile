FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY schema.prisma schema.prisma
RUN prisma generate

COPY . .

ENV PYTHONPATH "${PYTHONPATH}:/app"
ENV FLASK_APP=scripts/api.py
ENV FLASK_RUN_HOST=0.0.0.0

CMD ["flask", "run"]