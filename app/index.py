from flask import render_template, request, current_app as app
from flask_login import current_user
import datetime
import math

from .models.product import Product
from .models.purchase import Purchase
from .models.product_seller import ProductSeller
from .models.category import Category

from flask import Blueprint
bp = Blueprint('index', __name__)


@bp.route('/')
def index():
    category_id = request.args.get('category', type=int)
    query = request.args.get('q', type=str)
    sort = request.args.get('sort', default='price_asc', type=str)
    rating_threshold = request.args.get('rating_threshold', type=float)

    products = Product.search(category_id=category_id,
                              search=query,
                              sort=sort,
                              available=True,
                              rating_threshold=rating_threshold)
    per_page = 12
    page = request.args.get('page', 1, type=int)

    listings_by_product = ProductSeller.get_active_listings()

    if not category_id and not query and rating_threshold is None:
        active_product_ids = set(listings_by_product.keys())
        shown_ids = set(p.id for p in products)
        missing_ids = active_product_ids - shown_ids
        if missing_ids:
            for pid in missing_ids:
                prod = Product.get(pid)
                if prod:
                    products.append(prod)

    reverse_sort = sort == 'price_desc'
    products.sort(key=lambda p: (p.price, p.id), reverse=reverse_sort)

    total_products = len(products)
    total_pages = max(1, math.ceil(total_products / per_page)) if total_products else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_products = products[start:end]
                                                
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
    return render_template('index.html',
                           avail_products=paginated_products,
                           purchase_history=purchases,
                           product_listings=listings_by_product,
                           page=page,
                           total_pages=total_pages,
                           page_numbers=list(range(1, total_pages + 1)),
                           product_ratings=product_ratings,
                           categories=Category.get_all(),
                           selected_category=category_id,
                           query=query or '',
                           sort=sort,
                           rating_threshold=rating_threshold
                           )
