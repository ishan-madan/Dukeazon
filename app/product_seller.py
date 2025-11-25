from flask import Blueprint, render_template, current_app as app
from flask_login import current_user
from .models.product_seller import ProductSeller

bp = Blueprint('product_seller', __name__, url_prefix='/sellers')


@bp.route('/<int:seller_id>/inventory')
def seller_inventory(seller_id):
    # existing inventory data
    inventory = ProductSeller.get_inventory_by_sid(seller_id)

    # seller basic info (optional, but nice)
    seller_rows = app.db.execute("""
        SELECT id, firstname, lastname
        FROM Users
        WHERE id = :sid
    """, sid=seller_id)
    seller = seller_rows[0] if seller_rows else None

    # rating summary for this seller
    rating_rows = app.db.execute("""
        SELECT
            AVG(rating) AS avg_rating,
            COUNT(*)   AS num_reviews
        FROM seller_reviews
        WHERE seller_id = :sid
    """, sid=seller_id)
    seller_rating = rating_rows[0] if rating_rows else None

    # full list of reviews for this seller
    seller_reviews = app.db.execute("""
        SELECT
            sr.rating,
            sr.body,
            sr.created_at,
            u.firstname,
            u.lastname
        FROM seller_reviews sr
        JOIN Users u ON u.id = sr.user_id
        WHERE sr.seller_id = :sid
        ORDER BY sr.created_at DESC
    """, sid=seller_id)

    return render_template(
        'seller_inventory.html',
        seller_id=seller_id,
        seller=seller,
        inventory=inventory,
        seller_rating=seller_rating,
        seller_reviews=seller_reviews,
    )
