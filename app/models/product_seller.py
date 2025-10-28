from flask import Blueprint, render_template
from flask_login import login_required
from models.product_seller import ProductSeller

bp = Blueprint('product_seller', __name__, url_prefix='/sellers')


@bp.route('/<int:seller_id>/inventory')
@login_required
def seller_inventory(seller_id):
    """
    Render a seller's inventory as an HTML page.
    """
    # Fetch all listings for this seller
    inventory = ProductSeller.get_all_detailed_by_seller(seller_id)

    return render_template('seller_inventory.html', inventory=inventory)
