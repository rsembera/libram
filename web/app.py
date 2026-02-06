"""
Libram Flask Application
Main application factory and configuration.
"""

from __future__ import annotations

import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, g, session, jsonify

from core.database import Database

# App root is parent of 'web' directory
APP_ROOT = Path(__file__).parent.parent


def _get_or_create_secret_key() -> str:
    """Get secret key from file, or generate and store a new one."""
    key_path = APP_ROOT / 'data' / '.secret_key'

    if key_path.exists():
        return key_path.read_text().strip()

    # Generate a new key
    os.makedirs(key_path.parent, exist_ok=True)
    key = secrets.token_hex(32)
    key_path.write_text(key)
    # Restrict permissions (owner read/write only)
    key_path.chmod(0o600)
    return key


def create_app() -> Flask:
    """Create and configure the Flask application."""
    
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    # Configuration
    app.secret_key = os.environ.get('LIBRAM_SECRET_KEY') or _get_or_create_secret_key()
    app.config['SESSION_COOKIE_NAME'] = 'libram_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Database path
    app.config['DATABASE_PATH'] = os.environ.get(
        'LIBRAM_DB_PATH',
        str(APP_ROOT / 'data' / 'libram.db')
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
        except (ValueError, TypeError, OSError):
            return ''
    
    @app.template_filter('timestamp_to_short_date')
    def timestamp_to_short_date(timestamp):
        """Convert Unix timestamp to short date (Jan 15)."""
        if not timestamp:
            return ''
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%b %d')
        except (ValueError, TypeError, OSError):
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
    
    # Heartbeat update for desktop mode (on any request)
    @app.before_request
    def update_desktop_heartbeat():
        """Update heartbeat timestamp on any request for desktop mode."""
        heartbeat_func = app.config.get('HEARTBEAT_CALLBACK')
        if heartbeat_func:
            heartbeat_func()
    
    # Context processor to inject theme settings into all templates
    @app.context_processor
    def inject_theme_settings():
        """Inject theme, background_style, font_style, font_size, border_style, and rating colors into all templates."""
        try:
            db = get_db()
            return {
                'theme': db.get_setting('theme', 'ink'),
                'background_style': db.get_setting('background_style', ''),
                'font_style': db.get_setting('font_style', 'lexend'),
                'font_size': db.get_setting('font_size', 's'),
                'border_style': db.get_setting('border_style', 'accent'),
                'rating_5_color': db.get_setting('rating_5_color', ''),
                'rating_1_color': db.get_setting('rating_1_color', ''),
                'rating_5_name': db.get_setting('rating_5_name', 'Green'),
                'rating_1_name': db.get_setting('rating_1_name', 'Black')
            }
        except Exception:
            return {
                'theme': 'ink',
                'background_style': '',
                'font_style': 'lexend',
                'font_size': 's',
                'border_style': 'accent',
                'rating_5_color': '',
                'rating_1_color': '',
                'rating_5_name': 'Green',
                'rating_1_name': 'Black'
            }
    
    # Register blueprints
    from web.blueprints.auth import auth_bp
    from web.blueprints.books import books_bp
    from web.blueprints.settings import settings_bp
    from web.blueprints.backups import backups_bp
    from web.blueprints.types import types_bp
    from web.blueprints.exports import exports_bp
    from web.blueprints.covers import covers_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(backups_bp, url_prefix='/backups')
    app.register_blueprint(types_bp)
    app.register_blueprint(exports_bp)
    app.register_blueprint(covers_bp)
    
    # Session status API for timeout warning system
    @app.route('/api/session-status')
    def session_status():
        """Return session timeout status for frontend warning system."""
        if not session.get('logged_in'):
            return jsonify({'logged_in': False})
        
        db = get_db()
        try:
            timeout_minutes = int(db.get_setting('session_timeout', '30'))
        except (ValueError, TypeError):
            timeout_minutes = 30
        
        # If timeout is 0 ("Never"), no warning needed
        if timeout_minutes == 0:
            return jsonify({
                'logged_in': True,
                'timeout_minutes': 0,
                'seconds_remaining': None,
                'warning_needed': False
            })
        
        last_activity = session.get('last_activity', time.time())
        elapsed = time.time() - last_activity
        timeout_seconds = timeout_minutes * 60
        seconds_remaining = max(0, timeout_seconds - elapsed)
        
        # Warning threshold: 60 seconds before timeout
        warning_threshold = 60
        
        return jsonify({
            'logged_in': True,
            'timeout_minutes': timeout_minutes,
            'seconds_remaining': int(seconds_remaining),
            'warning_needed': seconds_remaining <= warning_threshold and seconds_remaining > 0
        })
    
    return app
