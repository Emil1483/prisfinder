import json
from flask import Flask
import os

from redis import Redis
from src.models.url import URLKey, URLValue

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = Redis.from_url(REDIS_URL)


@app.route("/provisioners", methods=["GET"])
def provisioners():
    def gen():
        for key in redis.scan_iter(f"provisioner:*"):
            yield key.decode()

    return [*gen()]


@app.route("/provisioners/<domain>", methods=["GET"])
def provisioner(domain):
    keys = redis.keys(f"provisioner:*:{domain}")
    if not keys:
        return f"provisioner with domain {domain} not found", 404

    key = keys[0].decode()
    value = json.loads(redis.get(key).decode())

    return {
        "value": value,
        "key": key,
    }


@app.route("/urls/<domain>/<cursor>", methods=["GET"])
def urls(domain, cursor):
    def gen():
        url_key = URLKey(domain=domain, id=cursor)
        url_value: URLValue = URLValue.from_json(redis.get(str(url_key)))

        yield url_key, url_value

        i = 1

        while url_value.next != cursor:
            if i >= 10:
                break

            url_key = URLKey(domain=domain, id=url_value.next)
            url_value: URLValue = URLValue.from_json(redis.get(str(url_key)))

            yield url_key, url_value
            i += 1

    return [{"key": key, "value": value} for key, value in gen()]


@app.route("/url/<domain>/<url_id>", methods=["GET"])
def url(domain, url_id):
    url_key = URLKey(domain=domain, id=url_id)
    url_value: URLValue = URLValue.from_json(redis.get(str(url_key)))

    return {"key": url_key, "value": url_value}


@app.route("/failed_urls/<domain>", methods=["GET"])
def failed_urls(domain):
    def gen():
        i = 0
        for key in redis.scan_iter(f"failed_url:{domain}:*"):
            i += 1
            if i > 10:
                break
            yield key.decode()

    return [*gen()]


if __name__ == "__main__":
    app.run(debug=True, port=8080)
