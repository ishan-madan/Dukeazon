from flask import (
    Blueprint, render_template, current_app as app,
    request, redirect, url_for, flash
)
from flask_login import login_required, current_user
from pathlib import Path

bp = Blueprint('social', __name__)

@bp.route('/social')
@login_required
def social_page():
    # Filter type: all | product | seller
    ftype = request.args.get('type', 'all').lower()
    if ftype not in ('all', 'product', 'seller'):
        ftype = 'all'

    # Limit: clamp between 1 and 50
    try:
        limit = int(request.args.get('limit', 5))
    except ValueError:
        limit = 5
    limit = max(1, min(limit, 50))

    # Load SQL file for recent feedback
    sql_path = Path(app.root_path).parent / 'sql' / 'get_recent_feedback.sql'
    sql = sql_path.read_text()

    rows = app.db.execute(sql, user_id=current_user.id, type=ftype, limit=limit)

    return render_template('social.html', rows=rows)


@bp.route('/products/<int:product_id>/review', methods=['GET', 'POST'])
@login_required
def product_review(product_id):
    """
    Create / edit / delete a review for a single product.
    One review per user per product.
    """

    # 1. Fetch the product
    product_rows = app.db.execute(
        """
        SELECT id, name, price
        FROM Products
        WHERE id = :pid
        """,
        pid=product_id
    )
    if not product_rows:
        flash("Product not found.")
        return redirect('/')

    product = product_rows[0]

    # 2. Handle POST: save or delete review
    if request.method == 'POST':
        # Delete case
        if 'delete' in request.form:
            app.db.execute(
                """
                DELETE FROM product_reviews
                WHERE product_id = :pid AND user_id = :uid
                """,
                pid=product_id, uid=current_user.id
            )
            flash("Review deleted.")
            return redirect(url_for('social.product_review', product_id=product_id))

        # Create / update case
        try:
            rating = int(request.form.get('rating', 0))
        except ValueError:
            rating = 0
        body = (request.form.get('body') or '').strip()

        if rating < 1 or rating > 5 or not body:
            flash("Please give a rating 1–5 and a non-empty comment.")
        else:
            # Check if this user already has a review for this product
            existing = app.db.execute(
                """
                SELECT product_review_id
                FROM product_reviews
                WHERE product_id = :pid AND user_id = :uid
                """,
                pid=product_id, uid=current_user.id
            )

            if existing:
                # Update existing review
                app.db.execute(
                    """
                    UPDATE product_reviews
                    SET rating = :rating,
                        body   = :body,
                        created_at = now()
                    WHERE product_review_id = :rid
                    """,
                    rating=rating,
                    body=body,
                    rid=existing[0].product_review_id
                )
            else:
                # Insert new review
                app.db.execute(
                    """
                    INSERT INTO product_reviews
                        (product_id, user_id, rating, body)
                    VALUES (:pid, :uid, :rating, :body)
                    """,
                    pid=product_id,
                    uid=current_user.id,
                    rating=rating,
                    body=body
                )

            flash("Review saved.")
            return redirect(url_for('social.product_review', product_id=product_id))

    # 3. Load this user's review (if any)
    user_review_rows = app.db.execute(
        """
        SELECT product_review_id, rating, body, created_at
        FROM product_reviews
        WHERE product_id = :pid AND user_id = :uid
        """,
        pid=product_id, uid=current_user.id
    )
    user_review = user_review_rows[0] if user_review_rows else None

    # 4. Load all reviews for this product
    all_reviews = app.db.execute(
        """
        SELECT pr.rating,
               pr.body,
               pr.created_at,
               u.firstname,
               u.lastname
        FROM product_reviews pr
        JOIN users u ON pr.user_id = u.id
        WHERE pr.product_id = :pid
        ORDER BY pr.created_at DESC
        """,
        pid=product_id
    )

    # 5. Summary (avg + count)
    summary_rows = app.db.execute(
        """
        SELECT AVG(rating) AS avg_rating,
               COUNT(*)    AS num_reviews
        FROM product_reviews
        WHERE product_id = :pid
        """,
        pid=product_id
    )
    rating_summary = summary_rows[0] if summary_rows else None

    return render_template(
        'product_review.html',
        product=product,
        user_review=user_review,
        all_reviews=all_reviews,
        rating_summary=rating_summary
    )


@bp.route('/my-reviews')
@login_required
def my_reviews():
    """
    List all reviews authored by the current user (product + seller),
    newest first, with links to edit.
    """
    product_reviews = app.db.execute(
        """
        SELECT pr.product_review_id,
               pr.product_id,
               pr.rating,
               pr.body,
               pr.created_at,
               p.name AS product_name
        FROM product_reviews pr
        JOIN products p ON pr.product_id = p.id
        WHERE pr.user_id = :uid
        ORDER BY pr.created_at DESC
        """,
        uid=current_user.id
    )

    seller_reviews = app.db.execute(
        """
        SELECT sr.seller_review_id,
               sr.seller_id,
               sr.rating,
               sr.body,
               sr.created_at,
               u.firstname,
               u.lastname
        FROM seller_reviews sr
        JOIN users u ON sr.seller_id = u.id
        WHERE sr.user_id = :uid
        ORDER BY sr.created_at DESC
        """,
        uid=current_user.id
    )

    return render_template(
        'my_reviews.html',
        product_reviews=product_reviews,
        seller_reviews=seller_reviews
    )


@bp.route('/sellers/<int:seller_id>/review', methods=['GET', 'POST'])
@login_required
def seller_review(seller_id):
    """
    Create / edit / delete a review for a seller.
    User must have purchased from this seller at least once.
    """

    # 1. Fetch seller
    seller_rows = app.db.execute(
        """
        SELECT id, firstname, lastname, email
        FROM Users
        WHERE id = :sid
        """,
        sid=seller_id
    )
    if not seller_rows:
        flash("Seller not found.")
        return redirect('/')

    seller = seller_rows[0]

    # 2. Check eligibility: must have purchased from this seller
    eligible_rows = app.db.execute(
        """
        SELECT 1
        FROM Purchases pu
        JOIN ProductSeller ps ON pu.pid = ps.product_id
        WHERE pu.uid = :uid
          AND ps.seller_id = :sid
        LIMIT 1
        """,
        uid=current_user.id,
        sid=seller_id
    )
    eligible = bool(eligible_rows)

    if request.method == 'POST':
        if not eligible:
            flash("You can only review sellers you have purchased from.")
            return redirect(url_for('social.seller_review', seller_id=seller_id))

        # Delete case
        if 'delete' in request.form:
            app.db.execute(
                """
                DELETE FROM seller_reviews
                WHERE seller_id = :sid AND user_id = :uid
                """,
                sid=seller_id, uid=current_user.id
            )
            flash("Seller review deleted.")
            return redirect(url_for('social.seller_review', seller_id=seller_id))

        # Create / update case
        try:
            rating = int(request.form.get('rating', 0))
        except ValueError:
            rating = 0
        body = (request.form.get('body') or '').strip()

        if rating < 1 or rating > 5 or not body:
            flash("Please give a rating 1–5 and a non-empty comment.")
        else:
            existing = app.db.execute(
                """
                SELECT seller_review_id
                FROM seller_reviews
                WHERE seller_id = :sid AND user_id = :uid
                """,
                sid=seller_id, uid=current_user.id
            )

            if existing:
                app.db.execute(
                    """
                    UPDATE seller_reviews
                    SET rating = :rating,
                        body   = :body,
                        created_at = now()
                    WHERE seller_review_id = :rid
                    """,
                    rating=rating,
                    body=body,
                    rid=existing[0].seller_review_id
                )
            else:
                app.db.execute(
                    """
                    INSERT INTO seller_reviews
                        (seller_id, user_id, rating, body)
                    VALUES (:sid, :uid, :rating, :body)
                    """,
                    sid=seller_id,
                    uid=current_user.id,
                    rating=rating,
                    body=body
                )

            flash("Seller review saved.")
            return redirect(url_for('social.seller_review', seller_id=seller_id))

    # 3. Load this user's review (if any)
    user_review_rows = app.db.execute(
        """
        SELECT seller_review_id, rating, body, created_at
        FROM seller_reviews
        WHERE seller_id = :sid AND user_id = :uid
        """,
        sid=seller_id, uid=current_user.id
    )
    user_review = user_review_rows[0] if user_review_rows else None

    # 4. All reviews for this seller
    all_reviews = app.db.execute(
        """
        SELECT sr.rating,
               sr.body,
               sr.created_at,
               u.firstname,
               u.lastname
        FROM seller_reviews sr
        JOIN users u ON sr.user_id = u.id
        WHERE sr.seller_id = :sid
        ORDER BY sr.created_at DESC
        """,
        sid=seller_id
    )

    # 5. Summary (avg + count)
    summary_rows = app.db.execute(
        """
        SELECT AVG(rating) AS avg_rating,
               COUNT(*)    AS num_reviews
        FROM seller_reviews
        WHERE seller_id = :sid
        """,
        sid=seller_id
    )
    rating_summary = summary_rows[0] if summary_rows else None

    return render_template(
        'seller_review.html',
        seller=seller,
        eligible=eligible,
        user_review=user_review,
        all_reviews=all_reviews,
        rating_summary=rating_summary
    )
