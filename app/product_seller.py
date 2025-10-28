from flask import Blueprint, jsonify
from flask_login import login_required
from models.product_seller import ProductSeller

bp = Blueprint('product_seller', __name__, url_prefix='/api/product_seller')


@bp.route('/<int:seller_id>/inventory', methods=['GET'])
@login_required
def get_inventory(seller_id):
    """
    Return the inventory for a given seller as JSON.
    """
    inventory = ProductSeller.get_all_detailed_by_seller(seller_id)

    # Convert to JSON-friendly dict
    result = []
    for item in inventory:
        result.append({
            "listing_id": item["listing_id"],
            "seller_id": item["seller_id"],
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "base_price": float(item["base_price"]),
            "seller_price": float(item["seller_price"]),
            "quantity": item["quantity"],
            "is_active": item["is_active"],
            "image_link": item["image_link"]
        })

    return jsonify(result)
