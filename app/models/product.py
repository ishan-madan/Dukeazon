from flask import current_app as app


class Product:
    def __init__(self, id, name, price, available):
        self.id = id
        self.name = name
        self.price = price
        self.available = available

    @staticmethod
    def get(id):
        rows = app.db.execute('''
SELECT id, name, price, available
FROM Products
WHERE id = :id
''',
                              id=id)
        return Product(*(rows[0])) if rows else None

    @staticmethod
    def get_all(available=True):
        rows = app.db.execute('''
SELECT id, name, price, available
FROM Products
WHERE available = :available
''',
                              available=available)
        return [Product(*row) for row in rows]

    @staticmethod
    def get_top_expensive(k):
        if k is None or k <= 0:
            raise ValueError("Parameter 'k' must be a positive integer.")

        rows = app.db.execute('''
SELECT id, name, price, available
FROM Products
WHERE available = TRUE
ORDER BY price DESC, id ASC
LIMIT :k
''', k=k)

        return [Product(*row) for row in rows]

    @staticmethod
    def set_available(product_id, available=True):
        """
        Update the 'available' flag for a product.
        """
        app.db.execute('''
UPDATE Products
SET available = :available
WHERE id = :id
''', available=available, id=product_id)
