from flask import Blueprint, jsonify, render_template, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user

from .models.category import Category
from .models.product import Product
from .models.product_review import ProductReview
from .models.product_seller import ProductSeller
from .models.subscription import Subscription

bp = Blueprint('products', __name__, url_prefix='/products')


@bp.route('/<int:product_id>', methods=['GET'])
def detail(product_id):
    product = Product.get(product_id)
    if not product:
        abort(404)
    sellers = ProductSeller.get_active_by_product(product_id)
    reviews = ProductReview.get_for_product(product_id)
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
    return render_template('product_detail.html',
                           product=product,
                           sellers=sellers,
                           reviews=reviews,
                           suggestions=suggestions,
                           allow_subscription=allow_subscription,
                           subscription=existing_subscription,
                           subscription_options=frequency_options)


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
