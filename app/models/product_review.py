from flask import current_app as app


class ProductReview:
    def __init__(self, review_id, product_id, user_id, rating, body, created_at, firstname=None, lastname=None):
        self.review_id = review_id
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating
        self.body = body
        self.created_at = created_at
        self.firstname = firstname
        self.lastname = lastname

    @staticmethod
    def get_for_product(product_id):
        rows = app.db.execute('''
SELECT pr.product_review_id,
       pr.product_id,
       pr.user_id,
       pr.rating,
       pr.body,
       pr.created_at,
       u.firstname,
       u.lastname
FROM product_reviews pr
JOIN Users u ON u.id = pr.user_id
WHERE pr.product_id = :product_id
ORDER BY pr.created_at DESC
''', product_id=product_id)

        return [ProductReview(*row) for row in rows]
