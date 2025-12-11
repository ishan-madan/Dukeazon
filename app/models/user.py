from flask_login import UserMixin
from flask import current_app as app
from werkzeug.security import generate_password_hash, check_password_hash

from .. import login


class User(UserMixin):
    def __init__(self, id, email, firstname, lastname, address, balance, is_seller=False):
        self.id = id
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.address = address
        self.balance = balance
        self.is_seller = is_seller

    @staticmethod
    def get_by_auth(email, password):
        rows = app.db.execute("""
SELECT password, id, email, firstname, lastname, address, balance, is_seller
FROM Users
WHERE email = :email
""",
                              email=email)
        if not rows:                   
            return None
        elif not check_password_hash(rows[0][0], password):
                                
            return None
        else:
            return User(*(rows[0][1:]))

    @staticmethod
    def email_exists(email):
        rows = app.db.execute("""
SELECT email
FROM Users
WHERE email = :email
""",
                              email=email)
        return len(rows) > 0

    @staticmethod
    def register(email, password, firstname, lastname, address, is_seller=False):
        try:
            rows = app.db.execute("""
INSERT INTO Users(email, password, firstname, lastname, address, is_seller)
VALUES(:email, :password, :firstname, :lastname, :address, :is_seller)
RETURNING id
""",
                                  email=email,
                                  password=generate_password_hash(password),
                                  firstname=firstname, lastname=lastname,
                                  address=address, is_seller=is_seller)
            id = rows[0][0]
            return User.get(id)
        except Exception as e:
                                                                                      
                                                                   
            print(str(e))
            return None

    @staticmethod
    @login.user_loader
    def get(id):
        rows = app.db.execute("""
SELECT id, email, firstname, lastname, address, balance, is_seller
FROM Users
WHERE id = :id
""",
                              id=id)
        return User(*(rows[0])) if rows else None

    @staticmethod
    def update_account(uid, firstname, lastname, email, address):
        app.db.execute("""
UPDATE Users
SET firstname = :firstname,
    lastname = :lastname,
    email = :email,
    address = :address
WHERE id = :uid
""", firstname=firstname, lastname=lastname, email=email, address=address, uid=uid)

    @staticmethod
    def add_balance(uid, amount):
        app.db.execute("""
UPDATE Users
SET balance = balance + :amount
WHERE id = :uid
""", amount=amount, uid=uid)

    @staticmethod
    def withdraw_balance(uid, amount):
        app.db.execute("""
UPDATE Users
SET balance = balance - :amount
WHERE id = :uid
""", amount=amount, uid=uid)
