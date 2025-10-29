from flask import current_app as app

class Cart:
    def __init__(self, user_id, product_id, name, price, quantity):
        self.user_id = user_id
        self.product_id = product_id
        self.name = name
        self.price = price
        self.quantity = quantity

    @staticmethod
    def get_by_user(user_id):
        rows = app.db.execute(f"""
    SELECT c.user_id, p.id, p.name, p.price, c.quantity
    FROM cart c
    JOIN products p ON c.product_id = p.id
    WHERE c.user_id = {user_id}
    ORDER BY p.name
""")



        return [Cart(*row) for row in rows]
