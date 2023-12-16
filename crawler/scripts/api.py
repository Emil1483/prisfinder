from flask import Flask, request
import os

from src.models.provisioner import ProvisionerStatus
from src.helpers.flask_error_handler import error_handler
from src.services.redis_service import RedisService

import src.services.prisma_service as prisma


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
    redis.disable_provisioner(domain)

    return "OK"


@app.route("/provisioners/<domain>/enable", methods=["POST"])
@error_handler
def enable_provisioner(domain):
    redis.enable_provisioner(domain)

    return "OK"


@app.route("/products/<product_id>", methods=["PATCH"])
@error_handler
def patch_product(product_id: int):
    prisma.patch_product(int(product_id), **request.json)

    finn_query = request.json.get("finn_query")
    if finn_query:
        prisma.insert_pending_urls("finn.no", [str(product_id)])

        key, _ = redis.fetch_provisioner("finn.no")
        if key.status == ProvisionerStatus.disabled:
            redis.enable_provisioner("finn.no")

    return "OK"


if __name__ == "__main__":
    app.run(debug=True, port=8080)
