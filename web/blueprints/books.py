"""
Libram Books Blueprint
Main book CRUD operations and views.
"""

from __future__ import annotations

import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, session
from core.fortunes import get_fortune
from core.astrology import get_astrology_line
from core.thumbnails import delete_thumbnail

books_bp = Blueprint('books', __name__)

# App root is parent of 'web/blueprints' directory
APP_ROOT = Path(__file__).parent.parent.parent
COVERS_DIR = str(APP_ROOT / 'covers')


def _delete_cover_file(filename: Optional[str]) -> None:
    """Delete a cover file if it exists."""
    if not filename:
        return
    # Security: prevent path traversal
    if '..' in filename or '/' in filename:
        return
    filepath = os.path.join(COVERS_DIR, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
    delete_thumbnail(COVERS_DIR, filename)


@books_bp.route('/')
def index():
    """Main view - display all books grouped by year."""
    db = current_app.get_db()
    
    # Get books grouped by year
    books_by_year = db.get_books_by_year()
    
    # Get stats for info cards
    stats = db.get_stats()
    
    # Get current date for display
    now = datetime.now()
    current_date = now.strftime('%A, %B %d, %Y')
    
    # Get fortune from session (set at login)
    fortune = session.get('fortune') or get_fortune()
    
    # Get astrology line (calculated fresh since moon changes frequently)
    astrology = get_astrology_line()
    show_astrology = db.get_setting('show_astrology', '1') != '0'
    
    # Get view mode from query string or cookie
    view_mode = request.args.get('view', request.cookies.get('libram_view', 'detailed'))
    
    # Search query (?search=...) only pre-fills the search box; the
    # filtering itself is done client-side in main_view.js
    search = request.args.get('search', '').strip()
    
    # Get card order
    card_order = db.get_setting('card_order', 'pages,reading-chart,navigation').split(',')
        
    # Build year groups for template
    current_year = now.year
    year_groups = []
    for year, books in books_by_year.items():
        year_groups.append({
            'year': year,
            'books': books,
            'total': len(books),
            'is_current': year == current_year
        })
    
    return render_template('main_view.html',
                          year_groups=year_groups,
                          stats=stats,
                          current_year=current_year,
                          current_date=current_date,
                          fortune=fortune,
                          astrology=astrology,
                          show_astrology=show_astrology,
                          view_mode=view_mode,
                          search=search,
                          card_order=card_order)



@books_bp.route('/book/new', methods=['GET', 'POST'])
def add_book():
    """Add a new book."""
    db = current_app.get_db()
    
    if request.method == 'POST':
        data, errors = _parse_book_form()
        
        if errors:
            return render_template('book_form.html',
                                  mode='add',
                                  errors=errors,
                                  book=_book_for_form(data),
                                  **_get_form_context())
        
        db.add_book(**data)
        return redirect(url_for('books.index'))
    
    # GET - show empty form
    return render_template('book_form.html',
                          mode='add',
                          book=None,
                          **_get_form_context())


@books_bp.route('/book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """Edit an existing book."""
    db = current_app.get_db()
    book = db.get_book(book_id)
    
    if not book:
        return redirect(url_for('books.index'))
    
    if request.method == 'POST':
        # Check for delete action
        if request.form.get('action') == 'delete':
            db.delete_book(book_id)
            _delete_cover_file(book.get('cover_filename'))
            return redirect(url_for('books.index'))
        
        data, errors = _parse_book_form()
        
        if errors:
            return render_template('book_form.html',
                                  mode='edit',
                                  errors=errors,
                                  book=_book_for_form(data),
                                  book_id=book_id,
                                  **_get_form_context())
        
        db.update_book(book_id, **data)
        
        # Delete the old cover if it was replaced or removed. The "old cover"
        # is whatever the database had, not a value sent back by the form.
        old_cover = book.get('cover_filename')
        if old_cover and old_cover != data['cover_filename']:
            _delete_cover_file(old_cover)
        
        return redirect(url_for('books.index'))
    
    # GET - show form with existing data
    return render_template('book_form.html',
                          mode='edit',
                          book=book,
                          book_id=book_id,
                          **_get_form_context())


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_book_form() -> tuple[dict, list[str]]:
    """
    Parse and validate the add/edit book form.
    
    Returns (data, errors). `data` holds keyword arguments for
    Database.add_book() / update_book(); `errors` is a list of messages
    (empty when the form is valid).
    """
    form = request.form
    
    def to_int(field_name: str) -> Optional[int]:
        value = form.get(field_name, '').strip()
        return int(value) if value.isdigit() else None
    
    did_not_finish = form.get('did_not_finish') == '1'
    
    data = {
        'title': form.get('title', '').strip(),
        'subtitle': form.get('subtitle', '').strip(),
        'author': form.get('author', '').strip(),
        'pages': to_int('pages'),
        # Dates come from hidden fields in YYYY-MM-DD format
        'date_begun': _parse_date_from_form('date_begun'),
        'date_finished': _parse_date_from_form('date_finished'),
        'days_paused': to_int('days_paused') or 0,
        'rating': min(to_int('rating') or 0, 5),
        'did_not_finish': did_not_finish,
        # Only keep pages_completed if DNF is checked
        'pages_completed': to_int('pages_completed') if did_not_finish else None,
        'notes': form.get('notes', '').strip(),
        'type_id': to_int('type_id'),
        'isbn': form.get('isbn', '').strip().replace('-', '').replace(' ', '') or None,
        'cover_filename': form.get('cover_filename', '').strip() or None,
    }
    
    errors = []
    if not data['title']:
        errors.append('Title is required')
    if not data['author']:
        errors.append('Author is required')
    if not data['pages'] or data['pages'] < 1:
        errors.append('Pages must be a positive number')
    if not data['date_begun']:
        errors.append('Date begun is required')
    if data['date_begun'] and data['date_finished'] and data['date_finished'] < data['date_begun']:
        errors.append('Date finished cannot be before date begun')
    if not data['type_id']:
        errors.append('Type is required')
    
    return data, errors


def _book_for_form(data: dict) -> dict:
    """
    Shape parsed form data like a database book, for re-showing the form
    after a validation error with everything the user entered still in place
    (dates, rating, type and cover included).
    """
    book = dict(data)
    book['date_begun_date'] = data['date_begun']
    book['date_finished_date'] = data['date_finished']
    if not book['pages']:
        book['pages'] = request.form.get('pages', '').strip()
    return book


def _parse_date_from_form(field_name: str) -> Optional[date]:
    """Parse date from hidden field (YYYY-MM-DD format)."""
    date_str = request.form.get(field_name, '').strip()
    
    if not date_str:
        return None
    
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError):
        pass
    
    return None



def _get_form_context() -> dict:
    """Get common context for book forms including book types and rating names."""
    db = current_app.get_db()
    book_types = db.get_book_types_for_dropdown()
    rating_5_name = db.get_setting('rating_5_name', 'Green')
    rating_1_name = db.get_setting('rating_1_name', 'Black')
    return {
        'book_types': book_types,
        'rating_5_name': rating_5_name,
        'rating_1_name': rating_1_name
    }


@books_bp.route('/api/books-per-month')
def books_per_month():
    """API endpoint returning books finished per month for chart."""
    db = current_app.get_db()
    data = db.get_books_per_month(12)
    return jsonify(data)

@books_bp.route('/api/pages-per-day-by-month')
def pages_per_day_by_month():
    """API endpoint returning average pages per day by month for chart."""
    db = current_app.get_db()
    data = db.get_avg_pages_per_day_by_month(12)
    return jsonify(data)

@books_bp.route('/api/books-by-type')
def books_by_type():
    """API endpoint returning book counts by type for chart."""
    db = current_app.get_db()
    data = db.get_books_by_type_stats(6)
    return jsonify(data)

@books_bp.route('/api/pages-per-month')
def pages_per_month():
    """API endpoint returning pages per month (proportional attribution) for chart."""
    db = current_app.get_db()
    data = db.get_pages_per_month(12)
    return jsonify(data)

@books_bp.route('/api/books-by-rating')
def books_by_rating():
    """API endpoint returning all-time book counts by rating for chart."""
    db = current_app.get_db()
    data = db.get_books_by_rating_stats()
    rating_names = {
        5: db.get_setting('rating_5_name', 'Green'),
        4: 'Gold',
        3: 'Silver',
        2: 'Bronze',
        1: db.get_setting('rating_1_name', 'Black'),
    }
    for entry in data:
        entry['name'] = rating_names[entry['rating']]
    return jsonify(data)
