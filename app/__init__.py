from flask import Flask
from flask_login import LoginManager
from .config import Config
from .db import DB


login = LoginManager()
login.login_view = 'users.login'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.db = DB(app)
    login.init_app(app)

    from .index import bp as index_bp
    app.register_blueprint(index_bp)

    from .users import bp as user_bp
    app.register_blueprint(user_bp)

    from app.social import bp as social_bp
    app.register_blueprint(social_bp)

    from .product_seller import bp as product_seller_bp
    app.register_blueprint(product_seller_bp)
    
    from .cart import bp as cart_bp
    app.register_blueprint(cart_bp)

    return app
