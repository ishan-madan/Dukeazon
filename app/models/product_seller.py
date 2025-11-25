from flask import current_app as app


class ProductSeller:
    def __init__(self, id, seller_id, product_id, price, quantity, is_active):
        self.id = id
        self.seller_id = seller_id
        self.product_id = product_id
        self.price = price
        self.quantity = quantity
        self.is_active = is_active

    @staticmethod
    def get(id):
        """
        Get a specific product_seller entry by ID.
        """
        rows = app.db.execute('''
SELECT id, seller_id, product_id, price, quantity, is_active
FROM ProductSeller
WHERE id = :id
''', id=id)

        return ProductSeller(*(rows[0])) if rows else None

    @staticmethod
    def get_all_by_seller(seller_id):
        """
        Get all inventory items for a given seller.
        """
        rows = app.db.execute('''
SELECT ps.id, ps.seller_id, ps.product_id, ps.price, ps.quantity, ps.is_active
FROM ProductSeller ps
WHERE ps.seller_id = :seller_id
ORDER BY ps.id
''', seller_id=seller_id)

        return [ProductSeller(*row) for row in rows]

    @staticmethod
    def get_all_detailed_by_seller(seller_id):
        """
        Get a seller's inventory, joined with product details.
        """
        rows = app.db.execute('''
SELECT ps.id AS listing_id,
       ps.seller_id,
       ps.product_id,
       p.name AS product_name,
       p.price AS base_price,
       ps.price AS seller_price,
       ps.quantity,
       ps.is_active,
       p.image_link
FROM ProductSeller ps
JOIN Products p ON ps.product_id = p.id
WHERE ps.seller_id = :seller_id
ORDER BY p.name
''', seller_id=seller_id)

        result = []
        for row in rows:
            result.append({
                "listing_id": row[0],
                "seller_id": row[1],
                "product_id": row[2],
                "product_name": row[3],
                "base_price": row[4],
                "seller_price": row[5],
                "quantity": row[6],
                "is_active": row[7],
                "image_link": row[8]
            })
        return result

    @staticmethod
    def get_active_listings():
        rows = app.db.execute('''
SELECT ps.id,
       ps.product_id,
       ps.seller_id,
       ps.price,
       ps.quantity,
       u.firstname || ' ' || u.lastname AS seller_name
FROM ProductSeller ps
JOIN Users u ON ps.seller_id = u.id
WHERE ps.is_active = TRUE AND ps.quantity > 0
ORDER BY ps.product_id, ps.price
''')

        listings = {}
        for row in rows:
            listings.setdefault(row[1], []).append({
                "listing_id": row[0],
                "product_id": row[1],
                "seller_id": row[2],
                "price": row[3],
                "quantity": row[4],
                "seller_name": row[5]
            })
        return listings

    @staticmethod
    def add(seller_id, product_id, price, quantity, is_active=True):
        """
        Add a new product listing for a seller.
        """
        rows = app.db.execute('''
INSERT INTO ProductSeller (seller_id, product_id, price, quantity, is_active)
VALUES (:seller_id, :product_id, :price, :quantity, :is_active)
RETURNING id
''', seller_id=seller_id, product_id=product_id, price=price,
           quantity=quantity, is_active=is_active)

        return rows[0][0] if rows else None

    @staticmethod
    def update_quantity(id, new_quantity):
        """
        Update quantity for an existing listing.
        """
        app.db.execute('''
UPDATE ProductSeller
SET quantity = :new_quantity
WHERE id = :id
''', new_quantity=new_quantity, id=id)

    @staticmethod
    def deactivate(id):
        """
        Soft-delete a product listing by setting is_active = FALSE.
        """
        app.db.execute('''
UPDATE ProductSeller
SET is_active = FALSE
WHERE id = :id
''', id=id)

    @staticmethod
    def activate(id):
        """
        Re-activate a product listing by setting is_active = TRUE.
        """
        app.db.execute('''
UPDATE ProductSeller
SET is_active = TRUE
WHERE id = :id
''', id=id)

    @staticmethod
    def has_active_listings_for_product(product_id):
        """
        Return True if there exists at least one active listing with quantity > 0 for the given product.
        """
        rows = app.db.execute('''
SELECT 1
FROM ProductSeller
WHERE product_id = :product_id AND is_active = TRUE AND quantity > 0
LIMIT 1
''', product_id=product_id)
        return len(rows) > 0
