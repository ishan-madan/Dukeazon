from flask import current_app as app
from sqlalchemy import text


class Order:
    def __init__(self, id, user_id, created_at, status, total_amount,
                 shipping_street=None, shipping_city=None, shipping_state=None,
                 shipping_zip=None, shipping_apt=None):
        self.id = id
        self.user_id = user_id
        self.created_at = created_at
        self.status = status
        self.total_amount = total_amount
        self.shipping_street = shipping_street
        self.shipping_city = shipping_city
        self.shipping_state = shipping_state
        self.shipping_zip = shipping_zip
        self.shipping_apt = shipping_apt

    @staticmethod
    def _compose_shipping_address(street, apt, city, state, zip_code, fallback=None):
        """
        Combine individual shipping components into a single human-readable line.
        """
        components = []
        if street:
            first_line = street
            if apt:
                first_line = f"{street}, {apt}"
            components.append(first_line)
        elif apt:
            components.append(apt)

        line2_parts = [part for part in (city, state) if part]
        line2 = ", ".join(line2_parts)
        if zip_code:
            line2 = f"{line2} {zip_code}".strip() if line2 else zip_code
        if line2:
            components.append(line2)

        if not components and fallback:
            components.append(fallback)

        return ", ".join(components) if components else None

    @staticmethod
    def list_by_user(user_id):
        rows = app.db.execute("""
SELECT o.id,
       o.user_id,
       o.created_at,
       o.status,
       o.total_amount,
       COALESCE(COUNT(oi.id), 0) AS item_count,
       COALESCE(SUM(CASE WHEN oi.fulfilled THEN 1 ELSE 0 END), 0) AS fulfilled_count,
       MAX(oi.fulfillment_status) AS primary_fulfillment_status
FROM Orders o
LEFT JOIN OrderItems oi ON o.id = oi.order_id
WHERE o.user_id = :user_id
GROUP BY o.id, o.user_id, o.created_at, o.status, o.total_amount
ORDER BY o.created_at DESC
""", user_id=user_id)

        orders = []
        for row in rows:
            fulfillment_status = row[7] if row[7] else 'Order Placed'
            orders.append({
                "id": row[0],
                "user_id": row[1],
                "created_at": row[2],
                "status": row[3],
                "total_amount": row[4],
                "item_count": row[5],
                "fulfilled_count": row[6],
                "is_fulfilled": row[5] > 0 and row[5] == row[6],
                "fulfillment_status": fulfillment_status
            })
        return orders

    @staticmethod
    def get_with_items(user_id, order_id):
        order_rows = app.db.execute("""
SELECT id,
       user_id,
       created_at,
       status,
       total_amount,
       shipping_street,
       shipping_city,
       shipping_state,
       shipping_zip,
       shipping_apt
FROM Orders
WHERE id = :order_id AND user_id = :user_id
""", order_id=order_id, user_id=user_id)

        if not order_rows:
            return None

        order = Order(*order_rows[0])
        order.shipping_address = Order._compose_shipping_address(
            order.shipping_street,
            order.shipping_apt,
            order.shipping_city,
            order.shipping_state,
            order.shipping_zip
        )

        item_rows = app.db.execute("""
    SELECT oi.id,
           oi.listing_id,
           oi.product_id,
           p.name,
           oi.seller_id,
           u.firstname || ' ' || u.lastname AS seller_name,
           oi.unit_price,
           oi.quantity,
           oi.subtotal,
           oi.fulfilled,
           oi.fulfilled_at,
           COALESCE(oi.fulfillment_status, 'Order Placed')
    FROM OrderItems oi
    JOIN Products p ON oi.product_id = p.id
    JOIN Users u ON oi.seller_id = u.id
    WHERE oi.order_id = :order_id
    ORDER BY oi.id
    """, order_id=order_id)

        items = []
        for row in item_rows:
            items.append({
                "id": row[0],
                "listing_id": row[1],
                "product_id": row[2],
                "product_name": row[3],
                "seller_id": row[4],
                "seller_name": row[5],
                "unit_price": row[6],
                "quantity": row[7],
                "subtotal": row[8],
                "fulfilled": row[9],
                "fulfilled_at": row[10],
                "fulfillment_status": row[11]
            })

        is_fulfilled = len(items) > 0 and all(item["fulfilled"] for item in items)
        order_status = "fulfilled" if is_fulfilled else order.status

        return {
            "order": order,
            "items": items,
            "is_fulfilled": is_fulfilled,
            "display_status": order_status
        }

    @staticmethod
    def list_items_for_seller(seller_id, q=None, status=None):
        """
        Return all order items that belong to a given seller. If q is provided,
        filter by order id or buyer name (case-insensitive partial match).
        If status is provided, limit to orders with Orders.status matching it.
        Results are ordered by order created_at DESC then item id.
        """
        sql = """
SELECT oi.id,
       oi.order_id,
       oi.product_id,
       p.name,
       oi.quantity,
       oi.unit_price,
       oi.subtotal,
       oi.fulfilled,
       oi.fulfilled_at,
       COALESCE(oi.fulfillment_status, 'Order Placed') as fulfillment_status,
       o.user_id,
       bu.firstname || ' ' || bu.lastname AS buyer_name,
       bu.address AS buyer_address,
       o.created_at,
       o.status,
       o.total_amount,
       (SELECT COALESCE(SUM(quantity),0) FROM OrderItems WHERE order_id = o.id) AS total_items,
       o.shipping_street,
       o.shipping_city,
       o.shipping_state,
       o.shipping_zip,
       o.shipping_apt
FROM OrderItems oi
JOIN Orders o ON oi.order_id = o.id
JOIN Products p ON oi.product_id = p.id
JOIN Users bu ON o.user_id = bu.id
WHERE oi.seller_id = :seller_id
"""
        params = {"seller_id": seller_id}
        if q:
            sql += " AND (CAST(o.id AS TEXT) ILIKE :q_like OR (bu.firstname || ' ' || bu.lastname) ILIKE :q_like)"
            params["q_like"] = f"%{q}%"
        if status:
            sql += " AND o.status = :status"
            params["status"] = status
        sql += " ORDER BY o.created_at DESC, oi.id"

        rows = app.db.execute(sql, **params)

        items = []
        for row in rows:
            (item_id, order_id, product_id, product_name, quantity, unit_price, subtotal,
             fulfilled, fulfilled_at, fulfillment_status, buyer_id, buyer_name, buyer_address_fallback,
             order_created_at, order_status, order_total, order_total_items,
             shipping_street, shipping_city, shipping_state, shipping_zip, shipping_apt) = row

            shipping_address = Order._compose_shipping_address(
                shipping_street,
                shipping_apt,
                shipping_city,
                shipping_state,
                shipping_zip,
                fallback=buyer_address_fallback
            )
            items.append({
                "item_id": item_id,
                "order_id": order_id,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "fulfilled": fulfilled,
                "fulfilled_at": fulfilled_at,
                "fulfillment_status": fulfillment_status,
                "buyer_id": buyer_id,
                "buyer_name": buyer_name,
                "buyer_address": shipping_address,
                "order_created_at": order_created_at,
                "order_status": order_status,
                "order_total": order_total,
                "order_total_items": order_total_items,
                "shipping_address": shipping_address
            })
        return items

    @staticmethod
    def mark_item_fulfilled(seller_id, item_id):
        with app.db.engine.begin() as conn:
            row = conn.execute(text("""
UPDATE OrderItems
SET fulfilled = TRUE,
    fulfilled_at = now()
WHERE id = :item_id
  AND seller_id = :seller_id
  AND fulfilled = FALSE
RETURNING order_id
"""), {"item_id": item_id, "seller_id": seller_id}).first()

            if not row:
                raise ValueError("Order item not found or already fulfilled.")

            order_id = row[0]

            remaining = conn.execute(text("""
SELECT bool_and(fulfilled) AS all_fulfilled
FROM OrderItems
WHERE order_id = :order_id
"""), {"order_id": order_id}).scalar()

            if remaining:
                conn.execute(text("""
UPDATE Orders
SET status = 'fulfilled'
WHERE id = :order_id
"""), {"order_id": order_id})
            else:
                conn.execute(text("""
UPDATE Orders
SET status = 'partial'
WHERE id = :order_id AND status <> 'fulfilled'
"""), {"order_id": order_id})

    @staticmethod
    def update_item_status(seller_id, item_id, status):
        """
        Update the fulfillment_status for an order item. If status == 'Delivered', mark fulfilled=True and set fulfilled_at.
        After updating, recompute the containing order's aggregate status: 'fulfilled' if all delivered, 'shipped' if any shipped, else 'pending'.
        """
        valid = ('Order Placed', 'Shipped', 'Delivered')
        if status not in valid:
            raise ValueError('Invalid status')

        with app.db.engine.begin() as conn:
            # Update the item
            if status == 'Delivered':
                row = conn.execute(text("""
UPDATE OrderItems
SET fulfillment_status = :status,
    fulfilled = TRUE,
    fulfilled_at = now()
WHERE id = :item_id AND seller_id = :seller_id
RETURNING order_id
"""), {"status": status, "item_id": item_id, "seller_id": seller_id}).first()
            else:
                row = conn.execute(text("""
UPDATE OrderItems
SET fulfillment_status = :status,
    fulfilled = FALSE,
    fulfilled_at = NULL
WHERE id = :item_id AND seller_id = :seller_id
RETURNING order_id
"""), {"status": status, "item_id": item_id, "seller_id": seller_id}).first()

            if not row:
                raise ValueError("Order item not found or permission denied.")

            order_id = row[0]

            # Recompute aggregate order status
            rows = conn.execute(text("""
SELECT COUNT(*) FILTER (WHERE COALESCE(fulfillment_status,'Order Placed') = 'Delivered') AS delivered_count,
       COUNT(*) FILTER (WHERE COALESCE(fulfillment_status,'Order Placed') = 'Shipped') AS shipped_count,
       COUNT(*) AS total_count
FROM OrderItems
WHERE order_id = :order_id
"""), {"order_id": order_id}).first()

            delivered_count = rows[0]
            shipped_count = rows[1]
            total_count = rows[2]

            if delivered_count == total_count and total_count > 0:
                conn.execute(text("""
UPDATE Orders SET status = 'fulfilled' WHERE id = :order_id
"""), {"order_id": order_id})
            elif shipped_count > 0:
                conn.execute(text("""
UPDATE Orders SET status = 'shipped' WHERE id = :order_id
"""), {"order_id": order_id})
            else:
                conn.execute(text("""
UPDATE Orders SET status = 'pending' WHERE id = :order_id
"""), {"order_id": order_id})

    @staticmethod
    def get_user_purchases(user_id, q=None):
        base_sql = """
        SELECT oi.product_id,
               p.name AS product_name,
               oi.quantity,
               oi.unit_price,
               oi.subtotal,
               oi.fulfilled,
               oi.fulfilled_at,
               oi.order_id,
               o.created_at AS order_date,
               COALESCE(oi.fulfillment_status, 'Order Placed') AS fulfillment_status
        FROM OrderItems oi
        JOIN Orders o ON oi.order_id = o.id
        JOIN Products p ON oi.product_id = p.id
        WHERE o.user_id = :user_id
        """
        params = {"user_id": user_id}

        # If user provided a search keyword, apply filtering
        if q:
            base_sql += " AND p.name ILIKE :q"
            params["q"] = f"%{q}%"

        # Sort latest → oldest orders
        base_sql += " ORDER BY o.created_at DESC"

        rows = app.db.execute(base_sql, **params)

        result = []
        for row in rows:
            result.append({
                "product_id": row[0],
                "product_name": row[1],
                "quantity": row[2],
                "unit_price": row[3],
                "subtotal": row[4],
                "fulfilled": row[5],
                "fulfilled_at": row[6],
                "order_id": row[7],
                "order_date": row[8],
                "fulfillment_status": row[9]
            })
        return result

    @staticmethod
    def user_has_delivered_order_with_product(user_id, product_id):
        rows = app.db.execute('''
SELECT COUNT(*) FROM OrderItems oi
JOIN Orders o ON oi.order_id = o.id
WHERE o.user_id = :user_id AND oi.product_id = :product_id AND COALESCE(oi.fulfillment_status, 'Order Placed') = 'Delivered'
''', user_id=user_id, product_id=product_id)
        return rows[0][0] > 0
