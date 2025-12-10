from flask import current_app as app
from sqlalchemy import text


class Order:
    def __init__(self, id, user_id, created_at, status, total_amount):
        self.id = id
        self.user_id = user_id
        self.created_at = created_at
        self.status = status
        self.total_amount = total_amount

    @staticmethod
    def list_by_user(user_id):
        rows = app.db.execute("""
SELECT o.id,
       o.user_id,
       o.created_at,
       o.status,
       o.total_amount,
       COALESCE(COUNT(oi.id), 0) AS item_count,
       COALESCE(SUM(CASE WHEN oi.fulfilled THEN 1 ELSE 0 END), 0) AS fulfilled_count
FROM Orders o
LEFT JOIN OrderItems oi ON o.id = oi.order_id
WHERE o.user_id = :user_id
GROUP BY o.id, o.user_id, o.created_at, o.status, o.total_amount
ORDER BY o.created_at DESC
""", user_id=user_id)

        orders = []
        for row in rows:
            orders.append({
                "id": row[0],
                "user_id": row[1],
                "created_at": row[2],
                "status": row[3],
                "total_amount": row[4],
                "item_count": row[5],
                "fulfilled_count": row[6],
                "is_fulfilled": row[5] > 0 and row[5] == row[6]
            })
        return orders

    @staticmethod
    def get_with_items(user_id, order_id):
        order_rows = app.db.execute("""
SELECT id, user_id, created_at, status, total_amount
FROM Orders
WHERE id = :order_id AND user_id = :user_id
""", order_id=order_id, user_id=user_id)

        if not order_rows:
            return None

        order = Order(*order_rows[0])

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
       oi.fulfilled_at
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
                "fulfilled_at": row[10]
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
    def list_items_for_seller(seller_id, q=None):
        """
        Return all order items that belong to a given seller. If q is provided,
        filter by order id or buyer name (case-insensitive partial match).
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
       o.user_id,
       bu.firstname || ' ' || bu.lastname AS buyer_name,
       bu.address AS buyer_address,
       o.created_at,
       o.status,
       o.total_amount,
       (SELECT COALESCE(SUM(quantity),0) FROM OrderItems WHERE order_id = o.id) AS total_items
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
        sql += " ORDER BY o.created_at DESC, oi.id"

        rows = app.db.execute(sql, **params)

        items = []
        for row in rows:
            items.append({
                "item_id": row[0],
                "order_id": row[1],
                "product_id": row[2],
                "product_name": row[3],
                "quantity": row[4],
                "unit_price": row[5],
                "subtotal": row[6],
                "fulfilled": row[7],
                "fulfilled_at": row[8],
                "buyer_id": row[9],
                "buyer_name": row[10],
                "buyer_address": row[11],
                "order_created_at": row[12],
                "order_status": row[13],
                "order_total": row[14],
                "order_total_items": row[15]
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
        o.created_at AS order_date
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
                "order_date": row[8]
            })
        return result
