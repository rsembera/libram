"""
Libram Covers Blueprint
Book cover upload, search, and serving.
"""

import logging
import os
import re
import uuid
import requests
from pathlib import Path
from flask import Blueprint, g, request, jsonify, send_file, Response

from core.thumbnails import generate_thumbnail, delete_thumbnail

logger = logging.getLogger(__name__)

covers_bp = Blueprint('covers', __name__, url_prefix='/covers')

# App root is parent of 'web/blueprints' directory
APP_ROOT = Path(__file__).parent.parent.parent
COVERS_DIR = str(APP_ROOT / 'covers')

# Ensure covers directory exists
os.makedirs(COVERS_DIR, exist_ok=True)

# Filenames Libram itself generates: uuid4().hex + allowed extension.
# The orphan sweep only ever touches files matching this pattern.
_APP_GENERATED_COVER_RE = re.compile(r'^[0-9a-f]{32}\.(jpg|jpeg|png|gif|webp)$')

_ISBN_RE = re.compile(r'^(\d{9}[\dX]|\d{13})$')


# Cover filenames are unique per upload (uuid) and their contents never
# change, so the browser can keep them. "private": covers sit behind the
# login, so only the user's own browser should cache them.
_COVER_CACHE_CONTROL = 'private, max-age=31536000, immutable'


def _send_cover(path: str) -> Response:
    """Send a cover or thumbnail with long-lived browser caching."""
    response = send_file(path)
    response.headers['Cache-Control'] = _COVER_CACHE_CONTROL
    # No session cookie / Vary: Cookie on this response, or the browser's
    # cached copy would never match (see LibramSessionInterface)
    g.skip_session_cookie = True
    return response


def cleanup_orphaned_covers(db_path: str) -> int:
    """Delete app-generated cover files not referenced by any book.

    Orphans accumulate when a cover is uploaded but the book form is
    abandoned before saving. Runs at startup. Deliberately conservative:
    - Never deletes anything if the database can't be read
    - Only deletes files matching Libram's own uuid naming pattern
    
    Returns the number of covers removed.
    """
    from core.database import Database
    try:
        with Database(db_path) as db:
            cursor = db.conn.cursor()
            cursor.execute(
                "SELECT cover_filename FROM books WHERE cover_filename IS NOT NULL"
            )
            referenced = {row[0] for row in cursor.fetchall()}
    except Exception as e:
        logger.warning(f"Skipping orphaned cover cleanup (db unavailable): {e}")
        return 0
    
    covers = Path(COVERS_DIR)
    if not covers.exists():
        return 0
    
    removed = 0
    for f in covers.iterdir():
        if not f.is_file():
            continue
        if not _APP_GENERATED_COVER_RE.match(f.name):
            continue
        if f.name in referenced:
            continue
        try:
            f.unlink()
            delete_thumbnail(COVERS_DIR, f.name)
            removed += 1
        except Exception:
            pass
    
    if removed:
        logger.info(f"Removed {removed} orphaned cover(s)")
    return removed


@covers_bp.route('/thumb/<filename>')
def serve_thumb(filename: str) -> Response | tuple[str, int]:
    """Serve a cover thumbnail (falls back to original if no thumb exists)."""
    if not filename or filename == 'None':
        return '', 204

    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400

    # Try thumbnail first
    thumb_name = Path(filename).stem + '_thumb.jpg'
    thumb_path = os.path.join(COVERS_DIR, 'thumbs', thumb_name)

    if os.path.exists(thumb_path):
        return _send_cover(thumb_path)

    # Fall back to original (not cached long-term: a thumbnail may be
    # generated for this cover later, and should replace it)
    filepath = os.path.join(COVERS_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath)

    return '', 204


@covers_bp.route('/<filename>')
def serve_cover(filename: str) -> Response | tuple[str, int]:
    """Serve a full-size cover image."""
    if not filename or filename == 'None':
        return '', 204

    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400

    filepath = os.path.join(COVERS_DIR, filename)

    if not os.path.exists(filepath):
        return '', 204

    return _send_cover(filepath)


@covers_bp.route('/upload', methods=['POST'])
def upload_cover() -> tuple[Response, int] | Response:
    """Upload a cover image."""
    if 'cover' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400

    file = request.files['cover']

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400

    # Check file type
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''

    if ext not in allowed_extensions:
        return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400

    # Generate unique filename
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(COVERS_DIR, filename)

    try:
        file.save(filepath)
        generate_thumbnail(COVERS_DIR, filename)
        return jsonify({'status': 'ok', 'filename': filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@covers_bp.route('/search', methods=['POST'])
def search_cover() -> tuple[Response, int] | Response:
    """Search for a cover and book info on Open Library by ISBN."""
    isbn = request.form.get('isbn', '').strip()

    if not isbn:
        return jsonify({'status': 'error', 'message': 'ISBN required'}), 400

    isbn = isbn.replace('-', '').replace(' ', '').upper()

    # ISBN-10 (last character may be X) or ISBN-13. Anything else would be
    # passed straight into the Open Library URL below.
    if not _ISBN_RE.match(isbn):
        return jsonify({'status': 'error', 'message': 'That does not look like an ISBN (10 or 13 digits).'}), 400

    try:
        api_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        api_resp = requests.get(api_url, timeout=10)
        api_resp.raise_for_status()
        api_data = api_resp.json()

        book_key = f"ISBN:{isbn}"
        if book_key not in api_data:
            return jsonify({'status': 'not_found', 'message': 'ISBN not found in Open Library'})

        book_info = api_data[book_key]

        metadata = {
            'title': book_info.get('title', ''),
            'subtitle': book_info.get('subtitle', ''),
            'authors': ', '.join(a.get('name', '') for a in book_info.get('authors', [])),
            'pages': book_info.get('number_of_pages'),
        }

        filename = None
        if 'cover' in book_info:
            cover_url = book_info['cover'].get('large') or book_info['cover'].get('medium')
            if cover_url:
                img_resp = requests.get(cover_url, timeout=10)
                if img_resp.status_code == 200 and len(img_resp.content) >= 1000:
                    filename = f"{uuid.uuid4().hex}.jpg"
                    filepath = os.path.join(COVERS_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(img_resp.content)
                    generate_thumbnail(COVERS_DIR, filename)

        return jsonify({
            'status': 'ok',
            'filename': filename,
            'metadata': metadata
        })

    except requests.RequestException as e:
        return jsonify({'status': 'error', 'message': f'Failed to search: {str(e)}'}), 500
