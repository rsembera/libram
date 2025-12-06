"""
Libram Flask Application
Main application factory and configuration.
"""

import os
import time
from datetime import datetime
from flask import Flask, g

from core.database import Database


def create_app():
    """Create and configure the Flask application."""
    
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    # Configuration
    app.secret_key = os.environ.get('LIBRAM_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_COOKIE_NAME'] = 'libram_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Database path
    app.config['DATABASE_PATH'] = os.environ.get(
        'LIBRAM_DB_PATH',
        os.path.expanduser('~/libram/data/libram.db')
    )
    
    # Register template filters
    @app.template_filter('timestamp_to_date')
    def timestamp_to_date(timestamp):
        """Convert Unix timestamp to formatted date string."""
        if not timestamp:
            return ''
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%b %d, %Y')
        except:
            return ''
    
    @app.template_filter('timestamp_to_short_date')
    def timestamp_to_short_date(timestamp):
        """Convert Unix timestamp to short date (Jan 15)."""
        if not timestamp:
            return ''
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%b %d')
        except:
            return ''
    
    @app.template_filter('rating_star')
    def rating_star(rating):
        """Convert rating number to star display."""
        rating_map = {
            0: ('☆', 'none'),      # No rating
            1: ('★', 'black'),     # Black
            2: ('★', 'bronze'),    # Bronze
            3: ('★', 'silver'),    # Silver
            4: ('★', 'gold'),      # Gold
            5: ('★', 'green'),     # Green
        }
        star, css_class = rating_map.get(rating, ('☆', 'none'))
        return f'<span class="rating-star rating-{css_class}">{star}</span>'
    
    # Database connection management
    def get_db():
        """Get database connection for current request."""
        if 'db' not in g:
            g.db = Database(app.config['DATABASE_PATH'])
            g.db.connect()
        return g.db
    
    @app.teardown_appcontext
    def close_db(exception):
        """Close database connection at end of request."""
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    # Make get_db available to blueprints
    app.get_db = get_db
    
    # Context processor to inject theme settings into all templates
    @app.context_processor
    def inject_theme_settings():
        """Inject card_style and background_style into all templates."""
        try:
            db = get_db()
            return {
                'card_style': db.get_setting('card_style', 'tutti-frutti'),
                'background_style': db.get_setting('background_style', 'suit-grey')
            }
        except:
            return {
                'card_style': 'tutti-frutti',
                'background_style': 'suit-grey'
            }
    
    # Register blueprints
    from web.blueprints.auth import auth_bp
    from web.blueprints.books import books_bp
    from web.blueprints.settings import settings_bp
    from web.blueprints.backups import backups_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(backups_bp, url_prefix='/backups')
    
    return app
