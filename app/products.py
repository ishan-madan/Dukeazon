from flask import Blueprint, jsonify, render_template, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user

from .models.category import Category
from .models.product import Product
from .models.product_review import ProductReview
from .models.product_seller import ProductSeller

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
    categories = Category.get_all()

    return render_template('products.html',
                           products=products,
                           categories=categories,
                           selected_category=category_id,
                           query=query or '',
                           sort=sort,
                           rating_threshold=rating_threshold)


@bp.route('/<int:product_id>', methods=['GET'])
def detail(product_id):
    product = Product.get(product_id)
    if not product:
        abort(404)
    sellers = ProductSeller.get_active_by_product(product_id)
    uid = current_user.id if current_user.is_authenticated else None
    reviews = ProductReview.get_for_product(product_id, user_id=uid)
    suggestions = Product.similar(product, limit=4)
    return render_template('product_detail.html',
                           product=product,
                           sellers=sellers,
                           reviews=reviews,
                           suggestions=suggestions)


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
