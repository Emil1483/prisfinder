from flask import Blueprint
from src.helpers.flask_error_handler import error_handler

from api import redis

provisioners_bp = Blueprint("provisioners", __name__)


@provisioners_bp.route("/provisioners", methods=["GET"])
@error_handler
def provisioners():
    return [str(k) for k in redis.scan_provisioner_keys()]


@provisioners_bp.route("/provisioners/<domain>", methods=["GET"])
@error_handler
def provisioner(domain):
    key, value = redis.fetch_provisioner(domain)

    return {
        "key": str(key),
        "value": value.to_dict(),
    }


@provisioners_bp.route("/urls/<domain>/<cursor>", methods=["GET"])
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


@provisioners_bp.route("/url/<domain>/<url_id>", methods=["GET"])
@error_handler
def url(domain, url_id):
    key, value = redis.fetch_url(domain, url_id)

    return {"key": str(key), "value": value.to_dict()}


@provisioners_bp.route("/failed_urls/<domain>", methods=["GET"])
def failed_urls(domain):
    def gen():
        i = 0
        for key in redis.scan_failed_url_keys(domain):
            i += 1
            if i > 10:
                break
            yield str(key)

    return [*gen()]


@provisioners_bp.route("/provisioners/<domain>/disable", methods=["POST"])
@error_handler
def disable_provisioner(domain):
    redis.disable_provisioner(domain)

    return "OK"


@provisioners_bp.route("/provisioners/<domain>/enable", methods=["POST"])
@error_handler
def enable_provisioner(domain):
    redis.enable_provisioner(domain)

    return "OK"
