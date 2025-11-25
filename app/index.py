from flask import render_template, current_app as app
from flask_login import current_user
import datetime

from .models.product import Product
from .models.purchase import Purchase

from flask import Blueprint
bp = Blueprint('index', __name__)


@bp.route('/')
def index():
    # get all available products for sale:
    products = Product.get_all(True)

    # find the products current user has bought:
    if current_user.is_authenticated:
        purchases = Purchase.get_all_by_uid_since(
            current_user.id, datetime.datetime(1980, 9, 14, 0, 0, 0)
        )
    else:
        purchases = None

    # rating summary for each product
    rows = app.db.execute("""
        SELECT
            product_id,
            AVG(rating) AS avg_rating,
            COUNT(*)   AS review_count
        FROM product_reviews
        GROUP BY product_id
    """)

    # build a dict: { product_id: {"avg": float, "count": int}, ... }
    product_ratings = {
        r.product_id: {
            "avg": float(r.avg_rating),
            "count": r.review_count
        }
        for r in rows
    }

    # render the page by adding information to the index.html file
    return render_template(
        'index.html',
        avail_products=products,
        purchase_history=purchases,
        product_ratings=product_ratings,
    )
