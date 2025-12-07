"""
Libram Settings Blueprint
Application configuration and preferences.
"""

from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from werkzeug.utils import secure_filename

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def settings_page():
    """Display settings page."""
    db = current_app.get_db()
    
    # Load current settings
    settings = {
        'theme': db.get_setting('theme', 'quiet-sky'),
        'background_style': db.get_setting('background_style', ''),
        'font_style': db.get_setting('font_style', 'libre-baskerville'),
        'session_timeout': db.get_setting('session_timeout', '30'),
    }
    
    # Card positions (3 cards)
    card_order = db.get_setting('card_order', 'pages-year,reading-chart,navigation')
    settings['card_positions'] = card_order.split(',')
    
    return render_template('settings.html', settings=settings)


@settings_bp.route('/api/theme', methods=['POST'])
def save_theme():
    """Save theme preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    theme = data.get('theme', 'quiet-sky')
    db.set_setting('theme', theme)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/background', methods=['POST'])
def save_background():
    """Save background preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    style = data.get('style', 'suit-grey')
    db.set_setting('background_style', style)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/font', methods=['POST'])
def save_font():
    """Save font preference."""
    db = current_app.get_db()
    data = request.get_json()
    
    style = data.get('style', 'libre-baskerville')
    db.set_setting('font_style', style)
    
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


# ============================================================================
# BACKGROUND IMAGES
# ============================================================================

@settings_bp.route('/api/backgrounds')
def list_backgrounds():
    """Return list of user-uploaded backgrounds."""
    # User backgrounds (uploaded)
    user_dir = Path(__file__).parent.parent / 'static' / 'user_backgrounds'
    user_backgrounds = []
    
    if user_dir.exists():
        for file in user_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                user_backgrounds.append({
                    'value': 'user:' + file.name,
                    'name': file.stem.replace('_', ' ').replace('-', ' ').title(),
                    'filename': file.name
                })
    
    return jsonify({
        'user': sorted(user_backgrounds, key=lambda x: x['name'])
    })


@settings_bp.route('/upload_background', methods=['POST'])
def upload_background():
    """Handle background image upload."""
    if 'background' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    
    file = request.files['background']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid file type. Use: png, jpg, jpeg, gif, or webp'})
    
    # Create safe filename
    filename = secure_filename(file.filename)
    
    # Create user_backgrounds directory if it doesn't exist
    upload_dir = Path(__file__).parent.parent / 'static' / 'user_backgrounds'
    upload_dir.mkdir(exist_ok=True)
    
    # Save file
    upload_path = upload_dir / filename
    
    try:
        file.save(str(upload_path))
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@settings_bp.route('/delete_background', methods=['POST'])
def delete_background():
    """Delete a user-uploaded background."""
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'})
    
    # Only allow deletion from user_backgrounds directory
    user_dir = Path(__file__).parent.parent / 'static' / 'user_backgrounds'
    file_path = user_dir / filename
    
    # Security check: ensure the path is within user_backgrounds
    try:
        file_path.resolve().relative_to(user_dir.resolve())
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid path'})
    
    if not file_path.exists():
        return jsonify({'success': False, 'error': 'File not found'})
    
    try:
        file_path.unlink()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
