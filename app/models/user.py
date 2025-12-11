from flask_login import UserMixin
from flask import current_app as app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import secrets

from .. import login


class User(UserMixin):
    def __init__(self, id, email, firstname, lastname, address, balance,
                 is_seller=False, created_at=None, email_verified=False,
                 verification_token=None, verification_sent_at=None):
        self.id = id
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.address = address
        self.balance = balance
        self.is_seller = is_seller
        self.created_at = created_at
        self.email_verified = email_verified
        self.verification_token = verification_token
        self.verification_sent_at = verification_sent_at

    @staticmethod
    def get_by_auth(email, password):
        rows = app.db.execute("""
SELECT password, id, email, firstname, lastname, address, balance, is_seller,
       created_at, email_verified, verification_token, verification_sent_at
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
    def issue_verification_token(uid):
        token = secrets.token_urlsafe(32)
        app.db.execute("""
UPDATE Users
SET verification_token = :token,
    verification_sent_at = now(),
    email_verified = FALSE
WHERE id = :uid
""", token=token, uid=uid)
        return token

    @staticmethod
    def mark_email_verified(token, max_age_hours=48):
        if not token:
            return None
        rows = app.db.execute("""
SELECT id, verification_sent_at
FROM Users
WHERE verification_token = :token
""", token=token)
        if not rows:
            return None
        uid, sent_at = rows[0]
        if sent_at:
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - sent_at > timedelta(hours=max_age_hours):
                return None
        app.db.execute("""
UPDATE Users
SET email_verified = TRUE,
    verification_token = NULL,
    verification_sent_at = NULL
WHERE id = :uid
""", uid=uid)
        return User.get(uid)

    @staticmethod
    @login.user_loader
    def get(id):
        rows = app.db.execute("""
SELECT id, email, firstname, lastname, address, balance, is_seller,
       created_at, email_verified, verification_token, verification_sent_at
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
