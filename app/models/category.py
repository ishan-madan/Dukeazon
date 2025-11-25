from flask import current_app as app


class Category:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    @staticmethod
    def get(category_id):
        rows = app.db.execute('''
SELECT id, name
FROM Categories
WHERE id = :category_id
''', category_id=category_id)
        return Category(*rows[0]) if rows else None

    @staticmethod
    def get_all():
        rows = app.db.execute('''
SELECT id, name
FROM Categories
ORDER BY name
''')
        return [Category(*row) for row in rows]
