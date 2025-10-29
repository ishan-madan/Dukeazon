from flask import Blueprint, jsonify, request

from .models.product import Product

bp = Blueprint('products', __name__, url_prefix='/products')


@bp.route('/top', methods=['GET'])
def top_products():
    """Return the top-k most expensive available products as JSON."""
    k = request.args.get('k', type=int)
    if k is None:
        return jsonify({"error": "Query parameter 'k' is required and must be an integer."}), 400
    if k <= 0:
        return jsonify({"error": "Query parameter 'k' must be positive."}), 400

    try:
        top_products = Product.get_top_expensive(k)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    payload = [{
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "available": product.available
    } for product in top_products]

    return jsonify({"products": payload})
