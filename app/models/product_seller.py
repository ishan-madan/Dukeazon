from flask import current_app as app
from datetime import datetime, timedelta


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
    def get_active_by_product(product_id):
        """
        Get active listings for a product with seller name, price, and quantity.
        """
        rows = app.db.execute('''
SELECT ps.id AS listing_id,
       ps.product_id,
       ps.seller_id,
       ps.price,
       ps.quantity,
       u.firstname || ' ' || u.lastname AS seller_name
FROM ProductSeller ps
JOIN Users u ON u.id = ps.seller_id
WHERE ps.product_id = :product_id
  AND ps.is_active = TRUE
  AND ps.quantity > 0
ORDER BY ps.price ASC, ps.id ASC
''', product_id=product_id)

        listings = []
        for row in rows:
            listings.append({
                "listing_id": row[0],
                "product_id": row[1],
                "seller_id": row[2],
                "price": row[3],
                "quantity": row[4],
                "seller_name": row[5]
            })
        return listings

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

    @staticmethod
    def analytics_for_seller(seller_id, days=30, limit=5):
        """
        Return analytics for a seller:
        - top_products: list of {product_id, product_name, units_sold, revenue}
        - timeseries: list of {date, units} for the last `days` days (inclusive)
        - totals: totals for the last `days` and all-time
        """
                                                    
        cutoff = datetime.utcnow() - timedelta(days=days)

                                    
        top_rows = app.db.execute('''
SELECT oi.product_id,
       p.name,
       COALESCE(SUM(oi.quantity),0) AS units_sold,
       COALESCE(SUM(oi.subtotal),0) AS revenue
FROM OrderItems oi
JOIN Orders o ON oi.order_id = o.id
JOIN Products p ON oi.product_id = p.id
WHERE oi.seller_id = :seller_id
  AND o.created_at >= :cutoff
  AND oi.fulfilled = TRUE
GROUP BY oi.product_id, p.name
ORDER BY units_sold DESC
LIMIT :limit
''', seller_id=seller_id, cutoff=cutoff, limit=limit)

        top_products = []
        for r in top_rows:
            top_products.append({
                "product_id": r[0],
                "product_name": r[1],
                "units_sold": int(r[2]) if r[2] is not None else 0,
                "revenue": float(r[3]) if r[3] is not None else 0.0
            })

                                                    
        ts_rows = app.db.execute('''
SELECT DATE(o.created_at) AS day,
       COALESCE(SUM(oi.quantity),0) AS units
FROM OrderItems oi
JOIN Orders o ON oi.order_id = o.id
WHERE oi.seller_id = :seller_id
  AND o.created_at >= :cutoff
  AND oi.fulfilled = TRUE
GROUP BY DATE(o.created_at)
ORDER BY day
''', seller_id=seller_id, cutoff=cutoff)

                                                                
        ts_map = {row[0].isoformat(): int(row[1]) for row in ts_rows}
        timeseries = []
        for i in range(days, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).date()
            key = d.isoformat()
            timeseries.append({"date": key, "units": ts_map.get(key, 0)})

                               
        totals_row = app.db.execute('''
SELECT COALESCE(SUM(oi.quantity),0) AS units,
       COALESCE(SUM(oi.subtotal),0) AS revenue
FROM OrderItems oi
JOIN Orders o ON oi.order_id = o.id
WHERE oi.seller_id = :seller_id
  AND o.created_at >= :cutoff
  AND oi.fulfilled = TRUE
''', seller_id=seller_id, cutoff=cutoff)
        totals_recent = totals_row[0] if totals_row else (0, 0.0)

                          
        all_row = app.db.execute('''
SELECT COALESCE(SUM(quantity),0) AS units,
       COALESCE(SUM(subtotal),0) AS revenue
FROM OrderItems
WHERE seller_id = :seller_id
  AND fulfilled = TRUE
''', seller_id=seller_id)
        totals_all = all_row[0] if all_row else (0, 0.0)

        return {
            "top_products": top_products,
            "timeseries": timeseries,
            "totals_recent": {"units": int(totals_recent[0] or 0), "revenue": float(totals_recent[1] or 0.0)},
            "totals_all": {"units": int(totals_all[0] or 0), "revenue": float(totals_all[1] or 0.0)}
        }

    @staticmethod
    def get_user_purchases_for_product(user_id, product_id):
        rows = app.db.execute('''
SELECT id FROM Purchases WHERE uid = :user_id AND pid = :product_id
''', user_id=user_id, product_id=product_id)
        return rows

    @staticmethod
    def get_user_delivered_orders_for_product(user_id, product_id):
        rows = app.db.execute('''
SELECT 1 FROM OrderItems oi
JOIN Orders o ON oi.order_id = o.id
WHERE o.user_id = :user_id AND oi.product_id = :product_id AND COALESCE(oi.fulfillment_status, 'Order Placed') = 'Delivered'
LIMIT 1
''', user_id=user_id, product_id=product_id)
        return bool(rows)
