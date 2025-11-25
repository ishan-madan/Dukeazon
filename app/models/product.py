from flask import current_app as app


class Product:
    def __init__(self, id, category_id, category_name, name, description, price, available, image_link, creator_id=None):
        self.id = id
        self.category_id = category_id
        self.category_name = category_name
        self.name = name
        self.description = description
        self.price = price
        self.available = available
        self.image_link = image_link
        self.creator_id = creator_id

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
    def search(category_id=None, search=None, sort='price_asc', available=True):
        sort_clause = 'price ASC'
        if sort == 'price_desc':
            sort_clause = 'price DESC'

        filters = []
        params = {}
        if available is not None:
            filters.append('available = :available')
            params['available'] = available
        if category_id:
            filters.append('category_id = :category_id')
            params['category_id'] = category_id
        if search:
            filters.append('(name ILIKE :q OR description ILIKE :q)')
            params['q'] = f'%{search}%'

        where_clause = ' AND '.join(filters) if filters else 'TRUE'

        rows = app.db.execute(
            f'''
SELECT id, category_id, category_name, name, description, price, available, image_link, creator_id
FROM Products
WHERE {where_clause}
ORDER BY {sort_clause}, id
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
