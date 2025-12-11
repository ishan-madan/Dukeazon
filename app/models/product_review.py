from flask import current_app as app


class ProductReview:
    def __init__(self, review_id, product_id, user_id, rating, body, created_at,
                 firstname=None, lastname=None, helpful_count=0, user_voted=False,
                 helpful_rank=None, verified=False):
        self.review_id = review_id
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating
        self.body = body
        self.created_at = created_at
        self.firstname = firstname
        self.lastname = lastname
        self.helpful_count = helpful_count or 0
        self.user_voted = bool(user_voted)
        self.helpful_rank = helpful_rank
        self.verified = bool(verified)

    @staticmethod
    def get_for_product(product_id, user_id=None, per_page=None, page=1, min_rating=None, sort='helpful'):
        """
        Fetch reviews for a product, including helpful-vote counts and whether
        the given user has marked each review as helpful.
        """
        uid = user_id or 0
        limit_clause = ""
        where_clauses = ["pr.product_id = :product_id"]
        order_clause = """
ORDER BY CASE WHEN helpful_rank <= 3 THEN 0 ELSE 1 END,
         helpful_rank,
         created_at DESC
"""
        params = {"product_id": product_id, "uid": uid}

        if min_rating is not None:
            where_clauses.append("pr.rating >= :min_rating")
            params["min_rating"] = min_rating

        sort = (sort or 'helpful').lower()
        if sort == 'recent':
            order_clause = "ORDER BY created_at DESC"

        if per_page:
            safe_page = max(1, int(page or 1))
            params["limit"] = int(per_page)
            params["offset"] = (safe_page - 1) * int(per_page)
            limit_clause = "LIMIT :limit OFFSET :offset"
        where_clause_str = " AND ".join(where_clauses)
        query = f'''
WITH aggregated AS (
    SELECT pr.product_review_id,
           pr.product_id,
           pr.user_id,
           pr.rating,
           pr.body,
           pr.created_at,
           u.firstname,
           u.lastname,
           COALESCE(SUM(rv.vote), 0) AS helpful_count,
           MAX(CASE WHEN rv.user_id = :uid THEN 1 ELSE 0 END) AS user_voted,
           MAX(CASE WHEN EXISTS (
                     SELECT 1 FROM Purchases pu
                     WHERE pu.uid = pr.user_id AND pu.pid = pr.product_id
                   ) THEN 1 ELSE 0 END) AS verified
    FROM product_reviews pr
    JOIN Users u ON u.id = pr.user_id
    LEFT JOIN review_votes rv
           ON rv.review_type = 'product'
          AND rv.review_id = pr.product_review_id
    WHERE {where_clause_str}
    GROUP BY pr.product_review_id, u.firstname, u.lastname
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY helpful_count DESC, created_at DESC) AS helpful_rank
    FROM aggregated
)
SELECT product_review_id,
       product_id,
       user_id,
       rating,
       body,
       created_at,
       firstname,
       lastname,
       helpful_count,
       COALESCE(user_voted, 0) AS user_voted,
       helpful_rank,
       COALESCE(verified, 0) AS verified
FROM ranked
{order_clause}
{limit_clause}
'''

        rows = app.db.execute(query, **params)

        return [ProductReview(*row) for row in rows]

class SellerReview:
    def __init__(self, review_id, seller_id, user_id, rating, body, created_at, firstname=None, lastname=None):
        self.review_id = review_id
        self.seller_id = seller_id
        self.user_id = user_id
        self.rating = rating
        self.body = body
        self.created_at = created_at
        self.firstname = firstname
        self.lastname = lastname

    @staticmethod
    def get_for_seller(seller_id):
        rows = app.db.execute('''
SELECT sr.seller_review_id,
       sr.seller_id,
       sr.user_id,
       sr.rating,
       sr.body,
       sr.created_at,
       u.firstname,
       u.lastname
FROM seller_reviews sr
JOIN Users u ON u.id = sr.user_id
WHERE sr.seller_id = :seller_id
ORDER BY sr.created_at DESC
''', seller_id=seller_id)

        return [SellerReview(*row) for row in rows]
