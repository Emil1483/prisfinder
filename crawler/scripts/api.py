import json
from flask import Flask
import os

from redis import Redis

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = Redis.from_url(REDIS_URL)


@app.route("/provisioners", methods=["GET"])
def provisioners():
    def gen():
        for key in redis.scan_iter(f"provisioner:*"):
            yield key.decode()

    return [*gen()]


@app.route("/provisioners/<key>", methods=["GET"])
def provisioner(key):
    return json.loads(redis.get(key).decode())


@app.route("/urls/<domain>", methods=["GET"])
def urls(domain):
    # Return :10 keys

    def gen():
        for key in redis.scan_iter(f"url:{domain}:*"):
            yield key.decode()

    return [*gen()]


if __name__ == "__main__":
    app.run(debug=True, port=8080)
