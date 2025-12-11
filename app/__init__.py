from datetime import timezone
from flask import Flask
from flask_login import LoginManager
from .config import Config
from .db import DB


login = LoginManager()
login.login_view = 'users.login'

from zoneinfo import ZoneInfo


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.db = DB(app)
    login.init_app(app)

    app.jinja_env.globals['eastern'] = ZoneInfo("America/New_York")

    def _ordinal(n):
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    @app.template_filter('friendly_datetime')
    def friendly_datetime(value):
        """
        Converts a datetime to Eastern timezone and formats as:
        'December 11th, 2025 at 9:34 AM'
        """
        if not value:
            return ''
        
        dt = value
        try:
            # If datetime is naive, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Convert to Eastern time
            dt = dt.astimezone(app.jinja_env.globals['eastern'])
        except Exception:
            pass

        month = dt.strftime('%B')        # Full month name
        day = _ordinal(dt.day)           # Day with ordinal suffix
        year = dt.strftime('%Y')         # Full year
        # 12-hour time, remove leading zero if present
        time_part = dt.strftime('%I:%M %p').lstrip('0') or dt.strftime('%I:%M %p')

        return f"{month} {day}, {year} at {time_part}"

    from .index import bp as index_bp
    app.register_blueprint(index_bp)

    from .products import bp as products_bp
    app.register_blueprint(products_bp)

    from .users import bp as user_bp
    app.register_blueprint(user_bp)

    from app.social import bp as social_bp
    app.register_blueprint(social_bp)

    from .product_seller import bp as product_seller_bp
    app.register_blueprint(product_seller_bp)
    
    from .cart import bp as cart_bp
    app.register_blueprint(cart_bp)

    return app
