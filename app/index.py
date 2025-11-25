from flask import render_template, request
from flask_login import current_user
import datetime
import math

from .models.product import Product
from .models.purchase import Purchase
from .models.product_seller import ProductSeller

from flask import Blueprint
bp = Blueprint('index', __name__)


@bp.route('/')
def index():
    # get all available products for sale:
    products = Product.get_all(True)
    per_page = 10
    page = request.args.get('page', 1, type=int)

    listings_by_product = ProductSeller.get_active_listings()

    # Ensure products that have active listings appear on the page even if the
    # Products.available flag is out-of-sync. Append any missing products that
    # have active listings so sellers' new listings show up immediately.
    active_product_ids = set(listings_by_product.keys())
    shown_ids = set(p.id for p in products)
    missing_ids = active_product_ids - shown_ids
    if missing_ids:
        for pid in missing_ids:
            prod = Product.get(pid)
            if prod:
                products.append(prod)

    # Force deterministic ordering by product id
    products.sort(key=lambda p: p.id)

    total_products = len(products)
    total_pages = max(1, math.ceil(total_products / per_page)) if total_products else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_products = products[start:end]
    # find the products current user has bought:
    if current_user.is_authenticated:
        purchases = Purchase.get_all_by_uid_since(
            current_user.id, datetime.datetime(1980, 9, 14, 0, 0, 0))
    else:
        purchases = None
    # render the page by adding information to the index.html file
    return render_template('index.html',
                           avail_products=paginated_products,
                           purchase_history=purchases,
                           product_listings=listings_by_product,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=list(range(1, total_pages + 1)))
