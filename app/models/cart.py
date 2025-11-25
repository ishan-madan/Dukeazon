from decimal import Decimal
from flask import current_app as app
from sqlalchemy import text


class Cart:
    def __init__(self, user_id, listing_id, product_id, product_name, seller_id,
                 seller_name, unit_price, quantity, subtotal):
        self.user_id = user_id
        self.listing_id = listing_id
        self.product_id = product_id
        self.product_name = product_name
        self.seller_id = seller_id
        self.seller_name = seller_name
        self.unit_price = unit_price
        self.quantity = quantity
        self.subtotal = subtotal

    @staticmethod
    def get_by_user(user_id):
        rows = app.db.execute("""
SELECT c.user_id,
       c.listing_id,
       c.product_id,
       p.name,
       c.seller_id,
       s.firstname || ' ' || s.lastname AS seller_name,
       c.unit_price,
       c.quantity,
       c.unit_price * c.quantity AS subtotal
FROM Cart c
JOIN Products p ON c.product_id = p.id
JOIN Users s ON c.seller_id = s.id
WHERE c.user_id = :user_id
ORDER BY p.name
""", user_id=user_id)

        return [Cart(*row) for row in rows]

    @staticmethod
    def add_item(user_id, listing_id, quantity=1):
        if quantity is None or quantity <= 0:
            raise ValueError("Quantity must be positive.")

        with app.db.engine.begin() as conn:
            listing = conn.execute(text("""
SELECT ps.id, ps.product_id, ps.seller_id, ps.price, ps.quantity, ps.is_active
FROM ProductSeller ps
WHERE ps.id = :listing_id
"""), {"listing_id": listing_id}).first()

            if not listing:
                raise ValueError("Listing not found.")

            if not listing[5] or listing[4] <= 0:
                raise ValueError("Listing is not available.")

            existing_qty = conn.execute(text("""
SELECT quantity FROM Cart
WHERE user_id = :user_id AND listing_id = :listing_id
"""), {"user_id": user_id, "listing_id": listing_id}).scalar()

            new_qty = quantity + (existing_qty or 0)
            if new_qty > listing[4]:
                raise ValueError("Requested quantity exceeds available inventory.")

            conn.execute(text("""
INSERT INTO Cart (user_id, product_id, listing_id, seller_id, unit_price, quantity)
VALUES (:user_id, :product_id, :listing_id, :seller_id, :unit_price, :quantity)
ON CONFLICT (user_id, listing_id) DO UPDATE
SET quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    product_id = EXCLUDED.product_id,
    seller_id = EXCLUDED.seller_id
"""), {
                "user_id": user_id,
                "product_id": listing[1],
                "listing_id": listing_id,
                "seller_id": listing[2],
                "unit_price": listing[3],
                "quantity": new_qty
            })

    @staticmethod
    def update_quantity(user_id, listing_id, quantity):
        if quantity is None or quantity < 0:
            raise ValueError("Quantity must be zero or positive.")

        if quantity == 0:
            Cart.remove_item(user_id, listing_id)
            return

        with app.db.engine.begin() as conn:
            listing = conn.execute(text("""
SELECT quantity, is_active
FROM ProductSeller
WHERE id = :listing_id
"""), {"listing_id": listing_id}).first()

            if not listing:
                raise ValueError("Listing not found.")

            available_qty, is_active = listing

            if not is_active:
                raise ValueError("Listing is not available.")

            if quantity > available_qty:
                raise ValueError("Requested quantity exceeds available inventory.")

            result = conn.execute(text("""
UPDATE Cart
SET quantity = :quantity
WHERE user_id = :user_id AND listing_id = :listing_id
"""), {"quantity": quantity, "user_id": user_id, "listing_id": listing_id})

            if result.rowcount == 0:
                raise ValueError("Cart item not found.")

    @staticmethod
    def remove_item(user_id, listing_id):
        app.db.execute("""
DELETE FROM Cart
WHERE user_id = :user_id AND listing_id = :listing_id
""", user_id=user_id, listing_id=listing_id)

    @staticmethod
    def clear(user_id):
        app.db.execute("""
DELETE FROM Cart
WHERE user_id = :user_id
""", user_id=user_id)

    @staticmethod
    def checkout(user_id):
        with app.db.engine.begin() as conn:
            cart_rows = conn.execute(text("""
SELECT c.listing_id,
       c.product_id,
       c.quantity,
       ps.seller_id,
       ps.price AS current_price,
       ps.quantity AS available_qty,
       p.name
FROM Cart c
JOIN ProductSeller ps ON c.listing_id = ps.id
JOIN Products p ON c.product_id = p.id
WHERE c.user_id = :user_id
FOR UPDATE
"""), {"user_id": user_id}).fetchall()

            if not cart_rows:
                raise ValueError("Your cart is empty.")

            balance_row = conn.execute(text("""
SELECT balance FROM Users WHERE id = :user_id FOR UPDATE
"""), {"user_id": user_id}).first()

            if not balance_row:
                raise ValueError("User not found.")

            balance = balance_row[0]

            line_items = []
            total_amount = Decimal("0")

            for row in cart_rows:
                listing_id, product_id, qty, seller_id, current_price, available_qty, product_name = row

                if qty > available_qty:
                    raise ValueError(f"Not enough inventory for {product_name}.")

                subtotal = Decimal(current_price) * qty
                line_items.append({
                    "listing_id": listing_id,
                    "product_id": product_id,
                    "seller_id": seller_id,
                    "quantity": qty,
                    "unit_price": current_price,
                    "subtotal": subtotal
                })
                total_amount += subtotal

            if balance < total_amount:
                raise ValueError("Insufficient balance to complete checkout.")

            order_row = conn.execute(text("""
INSERT INTO Orders (user_id, total_amount, status)
VALUES (:user_id, :total_amount, 'pending')
RETURNING id
"""), {"user_id": user_id, "total_amount": total_amount}).first()

            order_id = order_row[0]

            seller_totals = {}

            for item in line_items:
                conn.execute(text("""
INSERT INTO OrderItems (order_id, listing_id, seller_id, product_id, unit_price, quantity, subtotal)
VALUES (:order_id, :listing_id, :seller_id, :product_id, :unit_price, :quantity, :subtotal)
"""), {
                    "order_id": order_id,
                    "listing_id": item["listing_id"],
                    "seller_id": item["seller_id"],
                    "product_id": item["product_id"],
                    "unit_price": item["unit_price"],
                    "quantity": item["quantity"],
                    "subtotal": item["subtotal"]
                })

                conn.execute(text("""
UPDATE ProductSeller
SET quantity = quantity - :quantity
WHERE id = :listing_id
"""), {"quantity": item["quantity"], "listing_id": item["listing_id"]})

                seller_totals[item["seller_id"]] = seller_totals.get(item["seller_id"], Decimal("0")) + item["subtotal"]
                                                                                 
                                                                                 
                remaining = conn.execute(text("""
SELECT 1 FROM ProductSeller
WHERE product_id = :product_id AND is_active = TRUE AND quantity > 0
LIMIT 1
"""), {"product_id": item["product_id"]}).fetchone()
                if not remaining:
                    conn.execute(text("""
UPDATE Products
SET available = FALSE
WHERE id = :product_id
"""), {"product_id": item["product_id"]})

            conn.execute(text("""
UPDATE Users
SET balance = balance - :amount
WHERE id = :user_id
"""), {"amount": total_amount, "user_id": user_id})

            for seller_id, amount in seller_totals.items():
                conn.execute(text("""
UPDATE Users
SET balance = balance + :amount
WHERE id = :seller_id
"""), {"amount": amount, "seller_id": seller_id})

            conn.execute(text("""
DELETE FROM Cart
WHERE user_id = :user_id
"""), {"user_id": user_id})

            return order_id
