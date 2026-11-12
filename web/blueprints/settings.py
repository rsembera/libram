"""
Libram Settings Blueprint
Application configuration and preferences.
"""

from __future__ import annotations

from pathlib import Path
import re
from flask import Blueprint, render_template, request, current_app, jsonify
from werkzeug.utils import secure_filename

settings_bp = Blueprint('settings', __name__)

# Valid values for settings that accept a fixed set of options
VALID_THEMES = {'ink', 'slate', 'parchment', 'witching-hour', 'crimson-veil', 'terminal'}
VALID_FONTS = {'lexend', 'libre-baskerville', 'lora', 'source-sans', 'literata'}
VALID_FONT_SIZES = {'s', 'm', 'l'}
VALID_BORDER_STYLES = {'accent', 'vibrant'}
VALID_CARD_IDS = {'pages', 'reading-chart', 'navigation'}
VALID_TIMEOUTS = {'15', '30', '60', '120', '0'}

USER_BG_DIR = Path(__file__).parent.parent / 'static' / 'user_backgrounds'


@settings_bp.route('/')
def settings_page():
    """Display settings page."""
    db = current_app.get_db()
    
    # Load current settings
    settings = {
        'theme': db.get_setting('theme', 'ink'),
        'background_style': db.get_setting('background_style', ''),
        'font_style': db.get_setting('font_style', 'lexend'),
        'font_size': db.get_setting('font_size', 's'),
        'border_style': db.get_setting('border_style', 'accent'),
        'session_timeout': db.get_setting('session_timeout', '30'),
        'rating_5_color': db.get_setting('rating_5_color', '#10B981'),
        'rating_1_color': db.get_setting('rating_1_color', '#1F2937'),
        'rating_5_name': db.get_setting('rating_5_name', 'Green'),
        'rating_1_name': db.get_setting('rating_1_name', 'Black'),
        'show_astrology': db.get_setting('show_astrology', '1'),
    }
    
    # Card positions (3 cards)
    card_order = db.get_setting('card_order', 'pages,reading-chart,navigation')
    settings['card_positions'] = card_order.split(',')
    
    return render_template('settings.html', settings=settings)


@settings_bp.route('/api/theme', methods=['POST'])
def save_theme():
    """Save theme preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    theme = data.get('theme', 'ink')
    if theme not in VALID_THEMES:
        return jsonify({'status': 'error', 'message': 'Invalid theme'}), 400
    db.set_setting('theme', theme)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/background', methods=['POST'])
def save_background():
    """Save background preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    # '' = theme default; 'user:<filename>' = an uploaded background that exists
    style = data.get('style') or ''
    if style:
        name = style[5:] if style.startswith('user:') else ''
        if not name or name != Path(name).name or not (USER_BG_DIR / name).is_file():
            return jsonify({'status': 'error', 'message': 'Invalid background'}), 400
    db.set_setting('background_style', style)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/font', methods=['POST'])
def save_font():
    """Save font preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    style = data.get('style', 'lexend')
    if style not in VALID_FONTS:
        return jsonify({'status': 'error', 'message': 'Invalid font'}), 400
    db.set_setting('font_style', style)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/font-size', methods=['POST'])
def save_font_size():
    """Save font size preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    size = data.get('size', 's')
    if size not in VALID_FONT_SIZES:
        return jsonify({'status': 'error', 'message': 'Invalid font size'}), 400
    db.set_setting('font_size', size)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/show-astrology', methods=['POST'])
def save_show_astrology():
    """Save show astrology preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    show = '1' if data.get('show', True) else '0'
    db.set_setting('show_astrology', show)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/border-style', methods=['POST'])
def save_border_style():
    """Save border style preference (accent or vibrant)."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    style = data.get('style', 'accent')
    if style not in VALID_BORDER_STYLES:
        return jsonify({'status': 'error', 'message': 'Invalid border style'}), 400
    db.set_setting('border_style', style)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/rating-color', methods=['POST'])
def save_rating_color():
    """Save rating color preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    rating = data.get('rating')
    color = data.get('color', '')
    name = data.get('name', '')
    
    # Validate hex color format
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color or ''):
        return jsonify({'status': 'error', 'message': 'Invalid color'}), 400
    
    # Sanitize name (alphanumeric + spaces, max 20 chars)
    name = re.sub(r'[^a-zA-Z0-9 ]', '', name or '')[:20]
    
    if rating == 5:
        db.set_setting('rating_5_color', color)
        db.set_setting('rating_5_name', name)
    elif rating == 1:
        db.set_setting('rating_1_color', color)
        db.set_setting('rating_1_name', name)
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/card-order', methods=['POST'])
def save_card_order():
    """Save card order preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    order = data.get('order', [])
    if isinstance(order, list) and set(order) == VALID_CARD_IDS and len(order) == len(VALID_CARD_IDS):
        db.set_setting('card_order', ','.join(order))
    
    return jsonify({'status': 'ok'})


@settings_bp.route('/api/timeout', methods=['POST'])
def save_timeout():
    """Save session timeout preference."""
    db = current_app.get_db()
    data = request.get_json(silent=True) or {}
    
    timeout = str(data.get('timeout', 30))
    if timeout not in VALID_TIMEOUTS:
        return jsonify({'status': 'error', 'message': 'Invalid timeout'}), 400
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
    
    # Create safe filename (secure_filename can strip a non-ASCII name down
    # to nothing, or to just the extension)
    filename = secure_filename(file.filename)
    if '.' not in filename or not filename.rsplit('.', 1)[0]:
        filename = f'background.{file_ext}'
    
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
    data = request.get_json(silent=True) or {}
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
