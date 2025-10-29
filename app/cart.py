from flask import Blueprint, render_template, request
from .models.cart import Cart

bp = Blueprint('cart', __name__, url_prefix = '/cart')

@bp.route('/<int:user_id>', methods=['GET'])
def cart(user_id):
    # user_id = request.args.get('user_id', type=int)
    
    if not user_id:
        return "<h1>Missing user_id</h1>", 400


    items = Cart.get_by_user(user_id)
    total_price = sum(float(item.price) * item.quantity for item in items) if items else 0

    return render_template('cart.html',
                           title='My Cart',
                           user_id=user_id,
                           items=items,
                           total=total_price)
