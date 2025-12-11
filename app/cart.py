from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app as app
from flask_login import login_required, current_user

from .models.cart import Cart
from .models.order import Order
from types import SimpleNamespace

bp = Blueprint('cart', __name__, url_prefix='/cart')


def _ensure_owner(user_id):
    if not current_user.is_authenticated or current_user.id != user_id:
        abort(403)


def _handle_error(user_id, message, status_code=400):
    if request.is_json:
        return jsonify({"error": message}), status_code
    flash(message)
    return redirect(url_for('cart.cart', user_id=user_id))


@bp.route('/<int:user_id>', methods=['GET'])
@login_required
def cart(user_id):
    _ensure_owner(user_id)

    items = Cart.get_by_user(user_id)
    total_price = sum((item.subtotal for item in items), Decimal("0"))

    return render_template('cart.html',
                           title='My Cart',
                           user_id=user_id,
                           items=items,
                           total=total_price)


@bp.route('/<int:user_id>/add', methods=['POST'])
@login_required
def add_item(user_id):
    _ensure_owner(user_id)

    if request.is_json:
        listing_id = request.json.get('listing_id')
        quantity = request.json.get('quantity', 1)
    else:
        listing_id = request.form.get('listing_id', type=int)
        quantity = request.form.get('quantity', type=int)

    try:
        quantity = int(quantity) if quantity is not None else 1
    except (TypeError, ValueError):
        quantity = 1

    try:
        listing_id = int(listing_id) if listing_id is not None else None
    except (TypeError, ValueError):
        listing_id = None

    if not listing_id:
        return _handle_error(user_id, "Missing listing_id.")

    try:
        Cart.add_item(user_id, listing_id, quantity)
    except ValueError as exc:
        return _handle_error(user_id, str(exc))

    flash("Added to cart.")
    if request.is_json:
        return jsonify({"ok": True}), 200
    return redirect(url_for('cart.cart', user_id=user_id))


@bp.route('/<int:user_id>/update/<int:listing_id>', methods=['POST'])
@login_required
def update_item(user_id, listing_id):
    _ensure_owner(user_id)

    if request.is_json:
        quantity = request.json.get('quantity')
    else:
        quantity = request.form.get('quantity', type=int)

    try:
        quantity = int(quantity) if quantity is not None else None
    except (TypeError, ValueError):
        quantity = None

    try:
        Cart.update_quantity(user_id, listing_id, quantity)
    except ValueError as exc:
        return _handle_error(user_id, str(exc))

    flash("Updated cart item.")
    if request.is_json:
        return jsonify({"ok": True}), 200
    return redirect(url_for('cart.cart', user_id=user_id))


@bp.route('/<int:user_id>/remove/<int:listing_id>', methods=['POST'])
@login_required
def remove_item(user_id, listing_id):
    _ensure_owner(user_id)

    Cart.remove_item(user_id, listing_id)

    flash("Removed item from cart.")
    if request.is_json:
        return jsonify({"ok": True}), 200
    return redirect(url_for('cart.cart', user_id=user_id))


@bp.route('/<int:user_id>/checkout', methods=['POST'])
@login_required
def checkout(user_id):
    _ensure_owner(user_id)

    try:
        order_id = Cart.checkout(user_id)
    except ValueError as exc:
        return _handle_error(user_id, str(exc))

    flash("Order placed successfully.")
    if request.is_json:
        return jsonify({"order_id": order_id}), 200
    return redirect(url_for('cart.order_detail', user_id=user_id, order_id=order_id))


@bp.route('/<int:user_id>/orders', methods=['GET'])
@login_required
def orders(user_id):
    _ensure_owner(user_id)
    orders = Order.list_by_user(user_id)
    return render_template('orders.html',
                           title='My Orders',
                           user_id=user_id,
                           orders=orders)


@bp.route('/<int:user_id>/orders/<int:order_id>', methods=['GET'])
@login_required
def order_detail(user_id, order_id):
    _ensure_owner(user_id)
    data = Order.get_with_items(user_id, order_id)
    if not data:
        abort(404)

    # Determine which sellers (in this order) the current user has already reviewed
    seller_ids = sorted({item['seller_id'] for item in data["items"]})
    seller_reviews_map = {}
    if seller_ids:
        # Query seller_reviews for this user and these seller_ids
        rows = app.db.execute(
            """
            SELECT seller_id, seller_review_id
            FROM seller_reviews
            WHERE user_id = :uid
              AND seller_id = ANY(:sids)
            """,
            uid=current_user.id,
            sids=seller_ids
        )
        for r in rows:
            seller_reviews_map[r.seller_id] = r.seller_review_id

    return render_template('order_detail.html',
                           title=f"Order #{order_id}",
                           user_id=user_id,
                           order=data["order"],
                           items=data["items"],
                           display_status=data["display_status"],
                           is_fulfilled=data["is_fulfilled"],
                           seller_reviews_map=seller_reviews_map)


@bp.route('/seller/<int:seller_id>/fulfillment', methods=['GET'])
@login_required
def seller_orders_view(seller_id):
    _ensure_owner(seller_id)
    q = request.args.get('q')
    items = Order.list_items_for_seller(seller_id, q=q)

                                                                                            
    orders = []
    order_map = {}
    for it in items:
        oid = it['order_id']
        if oid not in order_map:
            order_obj = SimpleNamespace(
                order_id=oid,
                order_created_at=it['order_created_at'],
                buyer_id=it['buyer_id'],
                buyer_name=it['buyer_name'],
                buyer_address=it.get('buyer_address'),
                order_total=it.get('order_total'),
                order_total_items=it.get('order_total_items'),
                order_status=it.get('order_status'),
                items=[]
            )
            orders.append(order_obj)
            order_map[oid] = order_obj
        order_map[oid].items.append(it)

    return render_template('seller_orders.html',
                           title='Orders to Fulfill',
                           seller_id=seller_id,
                           orders=orders,
                           q=q)


@bp.route('/seller/<int:seller_id>/fulfillment/<int:item_id>', methods=['POST'])
@login_required
def fulfill_item(seller_id, item_id):
    _ensure_owner(seller_id)
    try:
        Order.mark_item_fulfilled(seller_id, item_id)
    except ValueError as exc:
        flash(str(exc), 'danger')
    else:
        flash("Marked item as fulfilled.", 'success')
    return redirect(url_for('cart.seller_orders_view', seller_id=seller_id))


@bp.route('/seller/<int:seller_id>/fulfillment/<int:item_id>/status', methods=['POST'])
@login_required
def update_item_status(seller_id, item_id):
    _ensure_owner(seller_id)
    status = request.form.get('status')
    try:
        Order.update_item_status(seller_id, item_id, status)
    except ValueError as exc:
        flash(str(exc), 'danger')
    else:
        flash(f"Updated status to '{status}'.", 'success')
    return redirect(url_for('cart.seller_orders_view', seller_id=seller_id))
