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
    
    # Get current time for display
    now = datetime.now()
    current_time = now.strftime('%I:%M %p').lstrip('0')
    current_date = now.strftime('%A, %B %d, %Y')
    
    # Get fortune from session (set at login)
    fortune = session.get('fortune') or get_fortune()
    
    # Get astrology line (calculated fresh since moon changes frequently)
    astrology = get_astrology_line()
    show_astrology = db.get_setting('show_astrology', '1') != '0'
    
    # Get view mode from query string or cookie
    view_mode = request.args.get('view', request.cookies.get('libram_view', 'detailed'))
    
    # Get search query
    search = request.args.get('search', '').strip()
    
    # Get card order
    card_order = db.get_setting('card_order', 'pages,reading-chart,navigation').split(',')
    
    # Filter books if search provided
    if search:
        search_lower = search.lower()
        filtered_by_year = {}
        for year, books in books_by_year.items():
            filtered = [b for b in books 
                       if search_lower in b['title'].lower() 
                       or search_lower in b['author'].lower()]
            if filtered:
                filtered_by_year[year] = filtered
        books_by_year = filtered_by_year
    
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
                          current_time=current_time,
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
        # Parse form data
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        author = request.form.get('author', '').strip()
        pages = request.form.get('pages', '')
        
        # Parse dates (from hidden fields with YYYY-MM-DD format)
        date_begun = _parse_date_from_form('date_begun')
        date_finished = _parse_date_from_form('date_finished')
        
        rating_str = request.form.get('rating', '0')
        rating = int(rating_str) if rating_str.isdigit() else 0
        days_paused = request.form.get('days_paused', '')
        days_paused = int(days_paused) if days_paused.isdigit() else 0
        did_not_finish = request.form.get('did_not_finish') == '1'
        pages_completed_str = request.form.get('pages_completed', '')
        # Only keep pages_completed if DNF is checked
        pages_completed = int(pages_completed_str) if (did_not_finish and pages_completed_str.isdigit()) else None
        notes = request.form.get('notes', '').strip()
        type_id = request.form.get('type_id', '')
        type_id = int(type_id) if type_id.isdigit() else None
        isbn = request.form.get('isbn', '').strip().replace('-', '').replace(' ', '') or None
        cover_filename = request.form.get('cover_filename', '').strip() or None
        
        # Validation
        errors = []
        if not title:
            errors.append('Title is required')
        if not author:
            errors.append('Author is required')
        if not pages or not pages.isdigit() or int(pages) < 1:
            errors.append('Pages must be a positive number')
        if not date_begun:
            errors.append('Date begun is required')
        if not type_id:
            errors.append('Type is required')
        
        if errors:
            return render_template('book_form.html',
                                  mode='add',
                                  errors=errors,
                                  book=request.form,
                                  **_get_form_context())
        
        # Create book
        db.add_book(
            title=title,
            subtitle=subtitle,
            author=author,
            pages=int(pages),
            date_begun=date_begun,
            date_finished=date_finished,
            days_paused=days_paused,
            rating=rating,
            did_not_finish=did_not_finish,
            notes=notes,
            type_id=type_id,
            pages_completed=pages_completed,
            isbn=isbn,
            cover_filename=cover_filename
        )
        
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
            # Delete cover file if exists
            if book.get('cover_filename'):
                _delete_cover_file(book['cover_filename'])
            db.delete_book(book_id)
            return redirect(url_for('books.index'))
        
        # Parse form data
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        author = request.form.get('author', '').strip()
        pages = request.form.get('pages', '')
        
        # Parse dates (from hidden fields with YYYY-MM-DD format)
        date_begun = _parse_date_from_form('date_begun')
        date_finished = _parse_date_from_form('date_finished')
        
        rating_str = request.form.get('rating', '0')
        rating = int(rating_str) if rating_str.isdigit() else 0
        days_paused = request.form.get('days_paused', '')
        days_paused = int(days_paused) if days_paused.isdigit() else 0
        did_not_finish = request.form.get('did_not_finish') == '1'
        pages_completed_str = request.form.get('pages_completed', '')
        # Only keep pages_completed if DNF is checked
        pages_completed = int(pages_completed_str) if (did_not_finish and pages_completed_str.isdigit()) else None
        notes = request.form.get('notes', '').strip()
        type_id = request.form.get('type_id', '')
        type_id = int(type_id) if type_id.isdigit() else None
        isbn = request.form.get('isbn', '').strip().replace('-', '').replace(' ', '') or None
        cover_filename = request.form.get('cover_filename', '').strip() or None
        original_cover = request.form.get('original_cover_filename', '').strip() or None
        
        # Validation
        errors = []
        if not title:
            errors.append('Title is required')
        if not author:
            errors.append('Author is required')
        if not pages or not pages.isdigit() or int(pages) < 1:
            errors.append('Pages must be a positive number')
        if not date_begun:
            errors.append('Date begun is required')
        if not type_id:
            errors.append('Type is required')
        
        if errors:
            return render_template('book_form.html',
                                  mode='edit',
                                  errors=errors,
                                  book=request.form,
                                  book_id=book_id,
                                  **_get_form_context())
        
        # Delete old cover if it changed
        if original_cover and original_cover != cover_filename:
            _delete_cover_file(original_cover)
        
        # Update book
        db.update_book(book_id,
            title=title,
            subtitle=subtitle,
            author=author,
            pages=int(pages),
            date_begun=date_begun,
            date_finished=date_finished,
            days_paused=days_paused,
            rating=rating,
            did_not_finish=did_not_finish,
            notes=notes,
            type_id=type_id,
            pages_completed=pages_completed,
            isbn=isbn,
            cover_filename=cover_filename
        )
        
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
