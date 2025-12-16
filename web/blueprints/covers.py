"""
Libram Covers Blueprint
Book cover upload, search, and serving.
"""

import os
import uuid
import requests
from flask import Blueprint, request, jsonify, send_file, Response

covers_bp = Blueprint('covers', __name__, url_prefix='/covers')

COVERS_DIR = os.path.expanduser('~/libram/covers')

# Ensure covers directory exists
os.makedirs(COVERS_DIR, exist_ok=True)


@covers_bp.route('/<filename>')
def serve_cover(filename: str) -> Response | tuple[str, int]:
    """Serve a cover image."""
    # Handle None/empty filenames gracefully
    if not filename or filename == 'None':
        return '', 204  # No content, no error
    
    # Security: prevent path traversal
    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400
    
    filepath = os.path.join(COVERS_DIR, filename)
    
    if not os.path.exists(filepath):
        return '', 204  # No content instead of 404
    
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
        return jsonify({'status': 'ok', 'filename': filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@covers_bp.route('/search', methods=['POST'])
def search_cover() -> tuple[Response, int] | Response:
    """Search for a cover on Open Library by ISBN."""
    isbn = request.form.get('isbn', '').strip()
    
    if not isbn:
        return jsonify({'status': 'error', 'message': 'ISBN required'}), 400
    
    # Clean ISBN (remove dashes/spaces)
    isbn = isbn.replace('-', '').replace(' ', '')
    
    try:
        # First, check the API to see if ISBN exists and has a cover
        api_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        api_resp = requests.get(api_url, timeout=10)
        api_data = api_resp.json()
        
        book_key = f"ISBN:{isbn}"
        if book_key not in api_data:
            return jsonify({'status': 'not_found', 'message': 'ISBN not found in Open Library'})
        
        book_info = api_data[book_key]
        if 'cover' not in book_info:
            return jsonify({'status': 'not_found', 'message': 'No cover available for this ISBN'})
        
        # Get the large cover image
        cover_url = book_info['cover'].get('large') or book_info['cover'].get('medium')
        if not cover_url:
            return jsonify({'status': 'not_found', 'message': 'No cover image available'})
        
        # Download the cover
        img_resp = requests.get(cover_url, timeout=10)
        if img_resp.status_code != 200 or len(img_resp.content) < 1000:
            return jsonify({'status': 'not_found', 'message': 'Failed to download cover image'})
        
        # Save the cover
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(COVERS_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(img_resp.content)
        
        return jsonify({'status': 'ok', 'filename': filename})
    
    except requests.RequestException as e:
        return jsonify({'status': 'error', 'message': f'Failed to search: {str(e)}'}), 500


@covers_bp.route('/delete/<filename>', methods=['POST'])
def delete_cover(filename: str) -> tuple[Response, int] | Response:
    """Delete a cover image."""
    # Security: prevent path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    filepath = os.path.join(COVERS_DIR, filename)
    
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass  # Ignore deletion errors
    
    return jsonify({'status': 'ok'})
