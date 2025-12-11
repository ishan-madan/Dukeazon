from flask import (
    Blueprint, render_template, current_app as app,
    request, redirect, url_for, flash
)
from flask_login import login_required, current_user
from pathlib import Path
from .models.product_review import ProductReview

bp = Blueprint('social', __name__)


@bp.route('/sellers/<int:seller_id>/reviews', methods=['GET'])
def public_seller_reviews(seller_id):
    """
    Public page: show all reviews for a seller and rating summary.
    Does not require login.
    """
    # 1. Fetch seller basic info
    seller_rows = app.db.execute(
        """
        SELECT id, firstname, lastname
        FROM Users
        WHERE id = :sid
        """,
        sid=seller_id
    )
    if not seller_rows:
        return render_template('seller_reviews_public.html', seller=None, all_reviews=None, rating_summary=None)

    seller = seller_rows[0]
    uid = current_user.id if current_user.is_authenticated else 0

    # 2. All reviews for this seller
    all_reviews = app.db.execute(
        """
        WITH aggregated AS (
            SELECT sr.seller_review_id,
                   sr.seller_id,
                   sr.user_id,
                   sr.rating,
                   sr.body,
                   sr.created_at,
                   u.firstname,
                   u.lastname,
                   COALESCE(SUM(rv.vote), 0) AS helpful_count,
                   MAX(CASE WHEN rv.user_id = :uid THEN 1 ELSE 0 END) AS user_voted
            FROM seller_reviews sr
            JOIN users u ON sr.user_id = u.id
            LEFT JOIN review_votes rv
                   ON rv.review_type = 'seller'
                  AND rv.review_id = sr.seller_review_id
            WHERE sr.seller_id = :sid
            GROUP BY sr.seller_review_id, u.firstname, u.lastname
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (ORDER BY helpful_count DESC, created_at DESC) AS helpful_rank
            FROM aggregated
        )
        SELECT *
        FROM ranked
        ORDER BY CASE WHEN helpful_rank <= 3 THEN 0 ELSE 1 END,
                 helpful_rank,
                 created_at DESC
        """,
        sid=seller_id,
        uid=uid
    )

    # 3. Summary (avg + count)
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

    return render_template('seller_reviews_public.html', seller=seller, all_reviews=all_reviews, rating_summary=rating_summary)

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


@bp.route('/reviews/helpful', methods=['POST'])
@login_required
def toggle_helpful_vote():
    """
    Mark or unmark a review (product or seller) as helpful for the current user.
    """
    review_type = (request.form.get('review_type') or request.form.get('type') or '').strip().lower()
    review_id_raw = request.form.get('review_id')
    try:
        review_id = int(review_id_raw)
    except (TypeError, ValueError):
        review_id = None
    action = request.form.get('action', 'add')
    next_url = request.form.get('next') or request.referrer or url_for('social.social_page')

    if review_type not in ('product', 'seller') or review_id is None:
        flash("Invalid review selection.")
        return redirect(next_url)

    # Validate that the review exists
    if review_type == 'product':
        table = 'product_reviews'
        id_col = 'product_review_id'
    else:
        table = 'seller_reviews'
        id_col = 'seller_review_id'

    exists = app.db.execute(
        f"SELECT 1 FROM {table} WHERE {id_col} = :rid LIMIT 1",
        rid=review_id
    )
    if not exists:
        flash("Review not found.")
        return redirect(next_url)

    if action == 'remove':
        app.db.execute(
            """
            DELETE FROM review_votes
            WHERE review_type = :rt AND review_id = :rid AND user_id = :uid
            """,
            rt=review_type, rid=review_id, uid=current_user.id
        )
        flash("Removed your helpful vote.")
    else:
        app.db.execute(
            """
            INSERT INTO review_votes(review_type, review_id, user_id, vote)
            VALUES (:rt, :rid, :uid, 1)
            ON CONFLICT (review_type, review_id, user_id)
            DO UPDATE SET vote = EXCLUDED.vote, created_at = now()
            """,
            rt=review_type, rid=review_id, uid=current_user.id
        )
        flash("Marked as helpful.")

    return redirect(next_url)


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

    # 3. Load all reviews (with helpful counts); find the current user's review
    all_reviews = ProductReview.get_for_product(product_id, user_id=current_user.id)
    user_review = next((r for r in all_reviews if r.user_id == current_user.id), None)

    # 4. Summary (avg + count)
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
               p.name AS product_name,
               (SELECT COUNT(*) FROM product_reviews WHERE product_id = pr.product_id) AS total_reviews_for_product
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
               u.lastname,
               (SELECT COUNT(*) FROM seller_reviews WHERE seller_id = sr.seller_id) AS total_reviews_for_seller
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

    # 3. All reviews for this seller (with helpful counts)
    all_reviews = app.db.execute(
        """
        WITH aggregated AS (
            SELECT sr.seller_review_id,
                   sr.seller_id,
                   sr.user_id,
                   sr.rating,
                   sr.body,
                   sr.created_at,
                   u.firstname,
                   u.lastname,
                   COALESCE(SUM(rv.vote), 0) AS helpful_count,
                   MAX(CASE WHEN rv.user_id = :uid THEN 1 ELSE 0 END) AS user_voted
            FROM seller_reviews sr
            JOIN users u ON sr.user_id = u.id
            LEFT JOIN review_votes rv
                   ON rv.review_type = 'seller'
                  AND rv.review_id = sr.seller_review_id
            WHERE sr.seller_id = :sid
            GROUP BY sr.seller_review_id, u.firstname, u.lastname
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (ORDER BY helpful_count DESC, created_at DESC) AS helpful_rank
            FROM aggregated
        )
        SELECT *
        FROM ranked
        ORDER BY CASE WHEN helpful_rank <= 3 THEN 0 ELSE 1 END,
                 helpful_rank,
                 created_at DESC
        """,
        sid=seller_id,
        uid=current_user.id
    )

    # Pick out the current user's review (if any)
    user_review = next((r for r in all_reviews if r.user_id == current_user.id), None)

    # 4. Summary (avg + count)
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
