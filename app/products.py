from flask import Blueprint, jsonify, render_template, request, abort, redirect, url_for, flash, current_app as app
from flask_login import login_required, current_user
import math

from .models.category import Category
from .models.product import Product
from .models.product_review import ProductReview
from .models.product_seller import ProductSeller
from .models.subscription import Subscription

bp = Blueprint('products', __name__, url_prefix='/products')


@bp.route('/', methods=['GET'])
def browse():
    category_id = request.args.get('category', type=int)
    query = request.args.get('q', type=str)
    sort = request.args.get('sort', default='price_asc', type=str)
    rating_threshold = request.args.get('rating_threshold', type=float)

    products = Product.search(category_id=category_id,
                              search=query,
                              sort=sort,
                              available=True,
                              rating_threshold=rating_threshold)
    # Build product rating summary for cards
    rating_map = {}
    if products:
        ids = [p.id for p in products]
        rows = app.db.execute(
            """
            SELECT product_id, AVG(rating)::float AS avg_rating, COUNT(*) AS review_count
            FROM product_reviews
            WHERE product_id = ANY(:ids)
            GROUP BY product_id
            """,
            ids=ids
        )
        rating_map = {r.product_id: {"avg": float(r.avg_rating), "count": r.review_count} for r in rows}
    categories = Category.get_all()

    return render_template('products.html',
                           products=products,
                           categories=categories,
                           selected_category=category_id,
                           query=query or '',
                           sort=sort,
                           rating_threshold=rating_threshold,
                           product_ratings=rating_map)


@bp.route('/<int:product_id>', methods=['GET'])
def detail(product_id):
    product = Product.get(product_id)
    if not product:
        abort(404)
    review_page = request.args.get('rpage', 1, type=int)
    review_sort = request.args.get('rsort', 'helpful')
    review_min_rating = request.args.get('rstars', type=int)
    per_page = 8
    sellers = ProductSeller.get_active_by_product(product_id)
    uid = current_user.id if current_user.is_authenticated else None
    reviews = ProductReview.get_for_product(product_id,
                                           user_id=uid,
                                           per_page=per_page,
                                           page=review_page,
                                           min_rating=review_min_rating,
                                           sort=review_sort)
    rating_summary = app.db.execute(
        """
        SELECT AVG(rating) AS avg_rating,
               COUNT(*)    AS num_reviews
        FROM product_reviews
        WHERE product_id = :pid
        """,
        pid=product_id
    )
    rating_summary = rating_summary[0] if rating_summary else None
    total_reviews = rating_summary.num_reviews if rating_summary else 0
    total_review_pages = max(1, math.ceil(total_reviews / per_page)) if total_reviews else 1
    # rating breakdown by star
    breakdown_rows = app.db.execute(
        """
        SELECT rating, COUNT(*) AS cnt
        FROM product_reviews
        WHERE product_id = :pid
        GROUP BY rating
        """,
        pid=product_id
    )
    rating_breakdown = {r.rating: r.cnt for r in breakdown_rows}

    suggestions = Product.similar(product, limit=4)
    allow_subscription = bool(product.category_name and product.category_name.lower().startswith('frozen treat'))
    existing_subscription = None
    if allow_subscription and current_user.is_authenticated:
        existing_subscription = Subscription.get_active_for_user_product(current_user.id, product_id)
    frequency_options = [
        ('weekly', 'Every Week'),
        ('monthly', 'Every Month'),
        ('quarterly', 'Every 3 Months')
    ]
    # Check if user has purchased this product
    has_purchased = False
    has_delivered_order = False
    if current_user.is_authenticated:
        purchase_rows = ProductSeller.get_user_purchases_for_product(current_user.id, product_id)
        has_purchased = bool(purchase_rows)
        has_delivered_order = ProductSeller.get_user_delivered_orders_for_product(current_user.id, product_id)
    return render_template('product_detail.html',
                           product=product,
                           sellers=sellers,
                           reviews=reviews,
                           rating_summary=rating_summary,
                           rating_breakdown=rating_breakdown,
                           review_page=review_page,
                           total_review_pages=total_review_pages,
                           review_sort=review_sort,
                           review_min_rating=review_min_rating,
                           per_page=per_page,
                           suggestions=suggestions,
                           allow_subscription=allow_subscription,
                           subscription=existing_subscription,
                           subscription_options=frequency_options,
                           has_purchased=has_purchased,
                           has_delivered_order=has_delivered_order)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    categories = Category.get_all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        image_link = request.form.get('image_link', '').strip() or None
        category_id = request.form.get('category_id', type=int)
        available = bool(request.form.get('available'))

        category = Category.get(category_id) if category_id else None
        if not category or not name or price is None:
            flash('Please fill out name, price, and category.', 'danger')
            return render_template('product_form.html',
                                   mode='create',
                                   categories=categories,
                                   product=None)
        pid = Product.create(category.id, category.name, name, description, price, available, image_link, current_user.id)
        flash('Product created.', 'success')
        return redirect(url_for('products.detail', product_id=pid))

    return render_template('product_form.html',
                           mode='create',
                           categories=categories,
                           product=None)


@bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    product = Product.get(product_id)
    if not product:
        abort(404)
    if product.creator_id != current_user.id:
        abort(403)

    categories = Category.get_all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        image_link = request.form.get('image_link', '').strip() or None
        category_id = request.form.get('category_id', type=int)
        available = bool(request.form.get('available'))

        category = Category.get(category_id) if category_id else None
        if not category or not name or price is None:
            flash('Please fill out name, price, and category.', 'danger')
            return render_template('product_form.html',
                                   mode='edit',
                                   categories=categories,
                                   product=product)

        Product.update(product_id, category.id, category.name, name, description, price, available, image_link)
        flash('Product updated.', 'success')
        return redirect(url_for('products.detail', product_id=product_id))

    return render_template('product_form.html',
                           mode='edit',
                           categories=categories,
                           product=product)


@bp.route('/<int:product_id>/subscribe', methods=['POST'])
@login_required
def subscribe(product_id):
    product = Product.get(product_id)
    if not product:
        abort(404)
    if not product.category_name or not product.category_name.lower().startswith('frozen treat'):
        flash('Subscriptions are only available for Frozen Treats.', 'warning')
        return redirect(url_for('products.detail', product_id=product_id))

    frequency = request.form.get('frequency')
    allowed = {'weekly', 'monthly', 'quarterly'}
    if frequency not in allowed:
        flash('Please choose a delivery frequency.', 'danger')
        return redirect(url_for('products.detail', product_id=product_id))

    Subscription.create_or_update(current_user.id, product_id, frequency)
    flash('Subscription saved! Manage it anytime from your account.', 'success')
    return redirect(url_for('products.detail', product_id=product_id))
