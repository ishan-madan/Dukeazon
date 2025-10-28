from flask import current_app as app


class Purchase:
    def __init__(self, id, uid, pid, time_purchased):
        self.id = id
        self.uid = uid
        self.pid = pid
        self.time_purchased = time_purchased

    @staticmethod
    def get(id):
        rows = app.db.execute('''
SELECT id, uid, pid, time_purchased
FROM Purchases
WHERE id = :id
''',
                              id=id)
        return Purchase(*(rows[0])) if rows else None

    @staticmethod
    def get_all_by_uid_since(uid, since):
        rows = app.db.execute('''
SELECT id, uid, pid, time_purchased
FROM Purchases
WHERE uid = :uid
AND time_purchased >= :since
ORDER BY time_purchased DESC
''',
                              uid=uid,
                              since=since)
        return [Purchase(*row) for row in rows]


    @staticmethod
    def get_all_detailed_by_uid(uid):
        """
        Return a user's purchase history, including product details and user name.
        """
        rows = app.db.execute('''
SELECT p.id AS purchase_id,
       p.uid AS user_id,
       u.firstname || ' ' || u.lastname AS user_name,
       pr.name AS product_name,
       pr.price AS product_price,
       pr.image_link,
       p.time_purchased
FROM Purchases p
JOIN Users u ON p.uid = u.id
JOIN Products pr ON p.pid = pr.id
WHERE p.uid = :uid
ORDER BY p.time_purchased DESC
''', uid=uid)

        result = []
        for row in rows:
            result.append({
                "purchase_id": row[0],
                "user_id": row[1],
                "user_name": row[2],
                "product_name": row[3],
                "product_price": row[4],
                "image_url": row[5],
                "time_purchased": row[6]
            })
        return result
