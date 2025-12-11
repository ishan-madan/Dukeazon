from flask import current_app as app


class ProductReview:
    def __init__(self, review_id, product_id, user_id, rating, body, created_at,
                 firstname=None, lastname=None, helpful_count=0, user_voted=False, helpful_rank=None):
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

    @staticmethod
    def get_for_product(product_id, user_id=None):
        """
        Fetch reviews for a product, including helpful-vote counts and whether
        the given user has marked each review as helpful.
        """
        uid = user_id or 0
        rows = app.db.execute('''
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
           MAX(CASE WHEN rv.user_id = :uid THEN 1 ELSE 0 END) AS user_voted
    FROM product_reviews pr
    JOIN Users u ON u.id = pr.user_id
    LEFT JOIN review_votes rv
           ON rv.review_type = 'product'
          AND rv.review_id = pr.product_review_id
    WHERE pr.product_id = :product_id
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
       helpful_rank
FROM ranked
ORDER BY CASE WHEN helpful_rank <= 3 THEN 0 ELSE 1 END,
         helpful_rank,
         created_at DESC
''', product_id=product_id, uid=uid)

        return [ProductReview(*row) for row in rows]
