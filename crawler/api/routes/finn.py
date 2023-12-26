from flask import Blueprint, request

from src.helpers.flask_error_handler import error_handler
from src.helpers.misc import hash_string
import src.services.prisma_service as prisma
from api import redis

finn_bp = Blueprint("finn", __name__)


@finn_bp.route("/finn_products/count", methods=["GET"])
@error_handler
def get_finn_products_count():
    count = prisma.count_products_with_finn_query()
    return {"count": count}


@finn_bp.route("/finn_products", methods=["GET"])
@error_handler
def get_finn_products():
    take = int(request.headers.get("take", "10"))
    skip = int(request.headers.get("skip", "0"))

    products = prisma.fetch_products_with_finn_query(
        page_size=take,
        skip=skip,
    )

    def gen():
        for product in products:
            url_id = hash_string(str(product.id))
            try:
                _, url_value = redis.fetch_url("finn.no", url_id)
                url_value.failed_at
                yield {
                    **product.to_dict(),
                    "scraped_at": url_value.scraped_at,
                    "failed_at": url_value.failed_at,
                }
            except KeyError:
                yield {
                    **product.to_dict(),
                    "scraped_at": None,
                    "failed_at": None,
                }

    return [*gen()]
