from flask import current_app as app


class Product:
    def __init__(self, id, category_id, category_name, name, description, price, available, image_link,
                 creator_id=None, avg_product_rating=None, product_review_count=None,
                 best_seller_rating=None, best_seller_review_count=None, listing_price=None):
        self.id = id
        self.category_id = category_id
        self.category_name = category_name
        self.name = name
        self.description = description
        self.base_price = price
        # price shown to buyers should reflect the active seller offers when available
        self.price = listing_price if listing_price is not None else price
        self.available = available
        self.image_link = image_link
        self.creator_id = creator_id
        # cached overall product rating + volume from product_reviews
        self.avg_product_rating = avg_product_rating
        self.product_review_count = product_review_count or 0
        # best seller rating summary derived from seller_reviews (respecting minimum review counts)
        self.best_seller_rating = best_seller_rating
        self.best_seller_review_count = best_seller_review_count or 0

    @staticmethod
    def get(id):
        rows = app.db.execute(
            '''
WITH active_prices AS (
    SELECT product_id, MIN(price) AS min_price
    FROM ProductSeller
    WHERE is_active = TRUE AND quantity > 0
    GROUP BY product_id
)
SELECT p.id,
       p.category_id,
       p.category_name,
       p.name,
       p.description,
       p.price,
       p.available,
       p.image_link,
       p.creator_id,
       ap.min_price
FROM Products p
LEFT JOIN active_prices ap
  ON ap.product_id = p.id
WHERE p.id = :id
''',
            id=id)
        if not rows:
            return None
        row = rows[0]
        return Product(*row[:-1], listing_price=row[-1])

    @staticmethod
    def get_all(available=True):
        rows = app.db.execute(
            '''
WITH active_prices AS (
    SELECT product_id, MIN(price) AS min_price
    FROM ProductSeller
    WHERE is_active = TRUE AND quantity > 0
    GROUP BY product_id
)
SELECT p.id,
       p.category_id,
       p.category_name,
       p.name,
       p.description,
       p.price,
       p.available,
       p.image_link,
       p.creator_id,
       ap.min_price
FROM Products p
LEFT JOIN active_prices ap
  ON ap.product_id = p.id
WHERE p.available = :available
ORDER BY p.id
''',
            available=available)
        return [Product(*row[:-1], listing_price=row[-1]) for row in rows]

    @staticmethod
    def search(category_id=None, search=None, sort='price_asc', available=True, rating_threshold=None):
        sort_clause = 'listing_price ASC'
        if sort == 'price_desc':
            sort_clause = 'listing_price DESC'

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
            having_clause = 'HAVING COALESCE(pr.avg_rating, 0) >= :rating_threshold'
            params['rating_threshold'] = rating_threshold

        rows = app.db.execute(
            f'''
WITH product_ratings AS (
    SELECT product_id, AVG(rating)::float AS avg_rating, COUNT(*) AS review_count
    FROM product_reviews
    GROUP BY product_id
),
seller_ratings AS (
    SELECT seller_id, AVG(rating)::float AS avg_rating, COUNT(*) AS review_count
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
    pr.avg_rating AS avg_product_rating,
    COALESCE(pr.review_count, 0) AS product_review_count,
    MAX(CASE WHEN sr.review_count >= 3 THEN sr.avg_rating END) AS best_seller_rating,
    MAX(CASE WHEN sr.review_count >= 3 THEN sr.review_count END) AS best_seller_review_count,
    COALESCE(MIN(ps.price), p.price) AS listing_price
FROM Products p
LEFT JOIN ProductSeller ps
  ON ps.product_id = p.id
 AND ps.is_active = TRUE
 AND ps.quantity > 0
LEFT JOIN product_ratings pr
  ON pr.product_id = p.id
LEFT JOIN seller_ratings sr
  ON sr.seller_id = ps.seller_id
WHERE {where_clause}
GROUP BY p.id, p.category_id, p.category_name, p.name, p.description, p.price, p.available, p.image_link, p.creator_id, pr.avg_rating, pr.review_count
{having_clause}
ORDER BY {sort_clause}, p.id
''',
            **params)
        result = []
        for row in rows:
            # unpack values: listing price is last column
            *base_fields, listing_price = row
            result.append(Product(*base_fields, listing_price=listing_price))
        return result

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
WITH active_prices AS (
    SELECT product_id, MIN(price) AS min_price
    FROM ProductSeller
    WHERE is_active = TRUE AND quantity > 0
    GROUP BY product_id
)
SELECT p.id,
       p.category_id,
       p.category_name,
       p.name,
       p.description,
       p.price,
       p.available,
       p.image_link,
       p.creator_id,
       ABS(COALESCE(ap.min_price, p.price) - :price) AS price_gap,
       COALESCE(ap.min_price, p.price) AS listing_price
FROM Products p
LEFT JOIN active_prices ap
  ON ap.product_id = p.id
WHERE p.available = TRUE
  AND p.id != :pid
  AND p.category_id = :cid
ORDER BY price_gap ASC, COALESCE(ap.min_price, p.price) ASC, p.id
LIMIT :limit
''',
            price=product.price,
            pid=product.id,
            cid=product.category_id,
            limit=limit)

        suggestions = []
        for row in rows:
            p = Product(*row[:9], listing_price=row[-1])
            p.price_gap = row[9]
            suggestions.append(p)
        return suggestions
