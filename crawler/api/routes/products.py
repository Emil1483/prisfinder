from flask import Blueprint, request

from src.models.provisioner import ProvisionerStatus
from src.helpers.flask_error_handler import error_handler
import src.services.prisma_service as prisma

from api import redis

products_bp = Blueprint("products", __name__)


@products_bp.route("/products/<product_id>", methods=["PATCH"])
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


@products_bp.route("/products/<product_id>", methods=["GET"])
@error_handler
def get_product(product_id):
    product = prisma.get_product_by_id(int(product_id))
    return product.to_dict()


@products_bp.route("/products", methods=["GET"])
@error_handler
def get_sample_products():
    products = prisma.fetch_products_sample(sample_size=10)
    return [p.to_dict() for p in products]
