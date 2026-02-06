"""
Libram Covers Blueprint
Book cover upload, search, and serving.
"""

import os
import uuid
import requests
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, Response

from core.thumbnails import generate_thumbnail, delete_thumbnail

covers_bp = Blueprint('covers', __name__, url_prefix='/covers')

# App root is parent of 'web/blueprints' directory
APP_ROOT = Path(__file__).parent.parent.parent
COVERS_DIR = str(APP_ROOT / 'covers')

# Ensure covers directory exists
os.makedirs(COVERS_DIR, exist_ok=True)


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
        return send_file(thumb_path)

    # Fall back to original
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

    return send_file(filepath)


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

    isbn = isbn.replace('-', '').replace(' ', '')

    try:
        api_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        api_resp = requests.get(api_url, timeout=10)
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


@covers_bp.route('/delete/<filename>', methods=['POST'])
def delete_cover(filename: str) -> tuple[Response, int] | Response:
    """Delete a cover image and its thumbnail."""
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400

    filepath = os.path.join(COVERS_DIR, filename)

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

    delete_thumbnail(COVERS_DIR, filename)

    return jsonify({'status': 'ok'})
