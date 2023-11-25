import itertools
import json
from flask import Flask
import os
from src.helpers.flask_error_handler import error_handler

from src.models.provisioner import ProvisionerStatus
from src.services.redis_service import RedisService

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis: RedisService = RedisService.from_url(REDIS_URL)


@app.route("/provisioners", methods=["GET"])
@error_handler
def provisioners():
    return [str(k) for k in redis.scan_provisioner_keys()]


@app.route("/provisioners/<domain>", methods=["GET"])
@error_handler
def provisioner(domain):
    key, value = redis.fetch_provisioner(domain)

    return {
        "key": str(key),
        "value": value.to_dict(),
    }


@app.route("/urls/<domain>/<cursor>", methods=["GET"])
@error_handler
def urls(domain, cursor):
    def gen():
        i = 0
        for url in redis.iter_urls(domain, cursor):
            i += 1
            if i > 10:
                break
            yield url

    return [{"key": key, "value": value} for key, value in gen()]


@app.route("/url/<domain>/<url_id>", methods=["GET"])
@error_handler
def url(domain, url_id):
    key, value = redis.fetch_url(domain, url_id)

    return {"key": str(key), "value": value.to_dict()}


@app.route("/failed_urls/<domain>", methods=["GET"])
def failed_urls(domain):
    def gen():
        i = 0
        for key in redis.scan_failed_url_keys(domain):
            i += 1
            if i > 10:
                break
            yield str(key)

    return [*gen()]


@app.route("/provisioners/<domain>/disable", methods=["POST"])
@error_handler
def disable_provisioner(domain):
    old_key, value = redis.fetch_provisioner(domain)
    new_key = old_key.with_status(ProvisionerStatus.disabled)
    redis.update_provisioner_key(old_key, new_key, value)

    return "OK"


@app.route("/provisioners/<domain>/enable", methods=["POST"])
@error_handler
def enable_provisioner(domain):
    old_key, value = redis.fetch_provisioner(domain)
    new_key = old_key.with_status(ProvisionerStatus.off)
    redis.update_provisioner_key(old_key, new_key, value)

    return "OK"


if __name__ == "__main__":
    app.run(debug=True, port=8080)
