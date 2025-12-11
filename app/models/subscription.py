from flask import current_app as app


class Subscription:
    TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS Subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES Products(id) ON DELETE CASCADE,
    frequency VARCHAR(20) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, product_id)
);
'''

    INDEX_SQL = '''
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON Subscriptions(user_id);
'''

    def __init__(self, id, user_id, product_id, frequency, active, created_at, product_name=None, category_name=None):
        self.id = id
        self.user_id = user_id
        self.product_id = product_id
        self.frequency = frequency
        self.active = active
        self.created_at = created_at
        self.product_name = product_name
        self.category_name = category_name

    @classmethod
    def _ensure_table(cls):
        app.db.execute(cls.TABLE_SQL)
        app.db.execute(cls.INDEX_SQL)

    @classmethod
    def create_or_update(cls, user_id, product_id, frequency):
        cls._ensure_table()
        rows = app.db.execute(
            '''
INSERT INTO Subscriptions (user_id, product_id, frequency, active)
VALUES (:user_id, :product_id, :frequency, TRUE)
ON CONFLICT (user_id, product_id)
DO UPDATE
SET frequency = EXCLUDED.frequency,
    active = TRUE,
    created_at = CURRENT_TIMESTAMP
RETURNING id
''',
            user_id=user_id,
            product_id=product_id,
            frequency=frequency)
        return rows[0][0] if rows else None

    @classmethod
    def get_active_for_user_product(cls, user_id, product_id):
        cls._ensure_table()
        rows = app.db.execute(
            '''
SELECT id, user_id, product_id, frequency, active, created_at
FROM Subscriptions
WHERE user_id = :user_id
  AND product_id = :product_id
  AND active = TRUE
LIMIT 1
''',
            user_id=user_id,
            product_id=product_id)
        return Subscription(*rows[0]) if rows else None

    @classmethod
    def get_active_by_user(cls, user_id):
        cls._ensure_table()
        rows = app.db.execute(
            '''
SELECT s.id,
       s.user_id,
       s.product_id,
       s.frequency,
       s.active,
       s.created_at,
       p.name,
       p.category_name
FROM Subscriptions s
JOIN Products p ON p.id = s.product_id
WHERE s.user_id = :user_id
  AND s.active = TRUE
ORDER BY s.created_at DESC
''',
            user_id=user_id)
        return [Subscription(*row[:6], product_name=row[6], category_name=row[7]) for row in rows]

    @classmethod
    def cancel(cls, subscription_id, user_id):
        cls._ensure_table()
        result = app.db.execute(
            '''
UPDATE Subscriptions
SET active = FALSE
WHERE id = :sid
  AND user_id = :uid
  AND active = TRUE
''',
            sid=subscription_id,
            uid=user_id)
        return result > 0
