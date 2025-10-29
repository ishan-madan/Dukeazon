from flask import render_template
from flask_login import current_user
import datetime

from .models.product import Product
from .models.purchase import Purchase

from .models.cart import Cart
from flask import request, jsonify

from flask import Blueprint
bp = Blueprint('index', __name__)


@bp.route('/')
def index():
    # get all available products for sale:
    products = Product.get_all(True)
    # find the products current user has bought:
    if current_user.is_authenticated:
        purchases = Purchase.get_all_by_uid_since(
            current_user.id, datetime.datetime(1980, 9, 14, 0, 0, 0))
    else:
        purchases = None
    # render the page by adding information to the index.html file
    return render_template('index.html',
                           avail_products=products,
                           purchase_history=purchases)

@bp.route('/cart', methods=['GET'])
def cart():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    items = Cart.get_by_user(user_id)
    return jsonify([{
        "product_id": i.product_id,
        "name": i.name,
        "price": i.price,
        "quantity": i.quantity
    } for i in items])