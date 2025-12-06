"""
Libram Settings Blueprint
Application configuration and preferences.
"""

from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def settings_page():
    """Display settings page."""
    db = current_app.get_db()
    
    # Load current settings
    settings = {
        'card_style': db.get_setting('card_style', 'tutti-frutti'),
        'background_style': db.get_setting('background_style', 'suit-grey'),
        'session_timeout': db.get_setting('session_timeout', '30'),
    }
    
    # Card positions (6 cards)
    card_order = db.get_setting('card_order', 
        'total-books,books-year,pages-year,avg-days,currently-reading,navigation')
    settings['card_positions'] = card_order.split(',')
    
    return render_template('settings.html', settings=settings)


@settings_bp.route('/api/card-style', methods=['POST'])
def save_card_style():
    """Save card style preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    style = data.get('style', 'tutti-frutti')
    db.set_setting('card_style', style)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/background', methods=['POST'])
def save_background():
    """Save background preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    style = data.get('style', 'suit-grey')
    db.set_setting('background_style', style)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/card-order', methods=['POST'])
def save_card_order():
    """Save card order preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    order = data.get('order', [])
    if order:
        db.set_setting('card_order', ','.join(order))
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/timeout', methods=['POST'])
def save_timeout():
    """Save session timeout preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    timeout = str(data.get('timeout', 30))
    db.set_setting('session_timeout', timeout)
    
    return jsonify({'status': 'ok'})
