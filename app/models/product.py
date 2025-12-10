from flask import current_app as app


class Product:
    def __init__(self, id, category_id, category_name, name, description, price, available, image_link, creator_id=None, best_seller_rating=None):
        self.id = id
        self.category_id = category_id
        self.category_name = category_name
        self.name = name
        self.description = description
        self.price = price
        self.available = available
        self.image_link = image_link
        self.creator_id = creator_id
        # highest average seller rating among active sellers for this product; None if no data
        self.best_seller_rating = best_seller_rating

    @staticmethod
    def get(id):
        rows = app.db.execute(
            '''
SELECT id, category_id, category_name, name, description, price, available, image_link, creator_id
FROM Products
WHERE id = :id
''',
            id=id)
        return Product(*rows[0]) if rows else None

    @staticmethod
    def get_all(available=True):
        rows = app.db.execute(
            '''
SELECT id, category_id, category_name, name, description, price, available, image_link, creator_id
FROM Products
WHERE available = :available
ORDER BY id
''',
            available=available)
        return [Product(*row) for row in rows]

    @staticmethod
    def search(category_id=None, search=None, sort='price_asc', available=True, rating_threshold=None):
        sort_clause = 'price ASC'
        if sort == 'price_desc':
            sort_clause = 'price DESC'

        filters = []
        params = {}
        if available is not None:
            filters.append('p.available = :available')
            params['available'] = available
        if category_id:
            filters.append('p.category_id = :category_id')
            params['category_id'] = category_id
        if search:
            filters.append('(p.name ILIKE :q OR p.description ILIKE :q)')
            params['q'] = f'%{search}%'

        where_clause = ' AND '.join(filters) if filters else 'TRUE'

        having_clause = ''
        if rating_threshold is not None:
            having_clause = 'HAVING COALESCE(MAX(sr.avg_rating), 0) >= :rating_threshold'
            params['rating_threshold'] = rating_threshold

        rows = app.db.execute(
            f'''
WITH seller_ratings AS (
    SELECT seller_id, AVG(rating)::float AS avg_rating
    FROM seller_reviews
    GROUP BY seller_id
)
SELECT
    p.id,
    p.category_id,
    p.category_name,
    p.name,
    p.description,
    p.price,
    p.available,
    p.image_link,
    p.creator_id,
    MAX(sr.avg_rating) AS best_seller_rating
FROM Products p
LEFT JOIN ProductSeller ps
  ON ps.product_id = p.id
 AND ps.is_active = TRUE
 AND ps.quantity > 0
LEFT JOIN seller_ratings sr
  ON sr.seller_id = ps.seller_id
WHERE {where_clause}
GROUP BY p.id, p.category_id, p.category_name, p.name, p.description, p.price, p.available, p.image_link, p.creator_id
{having_clause}
ORDER BY {sort_clause}, p.id
''',
            **params)
        return [Product(*row) for row in rows]

    @staticmethod
    def create(category_id, category_name, name, description, price, available, image_link, creator_id):
        row = app.db.execute(
            '''
INSERT INTO Products (category_id, category_name, name, description, price, available, image_link, creator_id)
VALUES (:category_id, :category_name, :name, :description, :price, :available, :image_link, :creator_id)
RETURNING id
''',
            category_id=category_id,
            category_name=category_name,
            name=name,
            description=description,
            price=price,
            available=available,
            image_link=image_link,
            creator_id=creator_id)
        return row[0][0] if row else None

    @staticmethod
    def update(product_id, category_id, category_name, name, description, price, available, image_link):
        app.db.execute(
            '''
UPDATE Products
SET category_id = :category_id,
    category_name = :category_name,
    name = :name,
    description = :description,
    price = :price,
    available = :available,
    image_link = :image_link
WHERE id = :product_id
''',
            category_id=category_id,
            category_name=category_name,
            name=name,
            description=description,
            price=price,
            available=available,
            image_link=image_link,
            product_id=product_id)

    @staticmethod
    def set_available(product_id, available=True):
        app.db.execute(
            '''
UPDATE Products
SET available = :available
WHERE id = :id
''',
            available=available,
            id=product_id)

    @staticmethod
    def similar(product, limit=4):
        """
        Return up to `limit` available products in the same category, ordered by closest price.
        """
        if product is None:
            return []
        rows = app.db.execute(
            '''
SELECT id, category_id, category_name, name, description, price, available, image_link, creator_id,
       ABS(price - :price) AS price_gap
FROM Products
WHERE available = TRUE
  AND id != :pid
  AND category_id = :cid
ORDER BY price_gap ASC, price ASC, id
LIMIT :limit
''',
            price=product.price,
            pid=product.id,
            cid=product.category_id,
            limit=limit)

        suggestions = []
        for row in rows:
            p = Product(*row[:9])
            p.price_gap = row[9]
            suggestions.append(p)
        return suggestions
