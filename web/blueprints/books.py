"""
Libram Books Blueprint
Main book CRUD operations and views.
"""

import csv
import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, current_app, Response, jsonify, session
from core.fortunes import get_fortune

books_bp = Blueprint('books', __name__)


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
    
    # Get view mode from query string or cookie
    view_mode = request.args.get('view', request.cookies.get('libram_view', 'detailed'))
    
    # Get search query
    search = request.args.get('search', '').strip()
    
    # Get theme settings
    card_style = db.get_setting('card_style', 'tutti-frutti')
    background_style = db.get_setting('background_style', 'suit-grey')
    
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
                          view_mode=view_mode,
                          search=search,
                          card_style=card_style,
                          background_style=background_style)


@books_bp.route('/book/new', methods=['GET', 'POST'])
def add_book():
    """Add a new book."""
    db = current_app.get_db()
    
    # Get theme settings
    card_style = db.get_setting('card_style', 'tutti-frutti')
    background_style = db.get_setting('background_style', 'suit-grey')
    
    if request.method == 'POST':
        # Parse form data
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        author = request.form.get('author', '').strip()
        pages = request.form.get('pages', '')
        
        # Parse dates (from hidden fields with YYYY-MM-DD format)
        date_begun = _parse_date_from_form('date_begun')
        date_finished = _parse_date_from_form('date_finished')
        
        rating = int(request.form.get('rating', 0))
        days_paused = request.form.get('days_paused', '')
        days_paused = int(days_paused) if days_paused.isdigit() else 0
        did_not_finish = request.form.get('did_not_finish') == '1'
        pages_completed_str = request.form.get('pages_completed', '')
        pages_completed = int(pages_completed_str) if pages_completed_str.isdigit() else None
        notes = request.form.get('notes', '').strip()
        type_id = request.form.get('type_id', '')
        type_id = int(type_id) if type_id.isdigit() else None
        
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
        
        if errors:
            return render_template('book_form.html',
                                  mode='add',
                                  errors=errors,
                                  book=request.form,
                                  **_get_date_options(),
                                  **_get_form_context())
        
        # Create book
        book_id = db.add_book(
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
            pages_completed=pages_completed
        )
        
        return redirect(url_for('books.index'))
    
    # GET - show empty form
    return render_template('book_form.html',
                          mode='add',
                          book=None,
                          **_get_date_options(),
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
            return redirect(url_for('books.index'))
        
        # Parse form data
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        author = request.form.get('author', '').strip()
        pages = request.form.get('pages', '')
        
        # Parse dates (from hidden fields with YYYY-MM-DD format)
        date_begun = _parse_date_from_form('date_begun')
        date_finished = _parse_date_from_form('date_finished')
        
        rating = int(request.form.get('rating', 0))
        days_paused = request.form.get('days_paused', '')
        days_paused = int(days_paused) if days_paused.isdigit() else 0
        did_not_finish = request.form.get('did_not_finish') == '1'
        pages_completed_str = request.form.get('pages_completed', '')
        pages_completed = int(pages_completed_str) if pages_completed_str.isdigit() else None
        notes = request.form.get('notes', '').strip()
        type_id = request.form.get('type_id', '')
        type_id = int(type_id) if type_id.isdigit() else None
        
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
        
        if errors:
            return render_template('book_form.html',
                                  mode='edit',
                                  errors=errors,
                                  book=request.form,
                                  book_id=book_id,
                                  **_get_date_options(),
                                  **_get_form_context())
        
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
            pages_completed=pages_completed
        )
        
        return redirect(url_for('books.index'))
    
    # GET - show form with existing data
    return render_template('book_form.html',
                          mode='edit',
                          book=book,
                          book_id=book_id,
                          **_get_date_options(),
                          **_get_form_context())


@books_bp.route('/export/csv')
def export_csv():
    """Export all books to CSV."""
    db = current_app.get_db()
    books = db.get_all_books()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'All-Time #', 'Year #', 'Title', 'Subtitle', 'Author', 'Pages',
        'Date Begun', 'Date Finished', 'Days', 'Days Paused', 'Pages/Day',
        'Rating', 'Did Not Finish', 'Pages Completed', 'Notes'
    ])
    
    # Rating labels
    rating_labels = {0: '', 1: 'Black', 2: 'Bronze', 3: 'Silver', 4: 'Gold', 5: 'Green'}
    
    # Data rows
    for book in books:
        writer.writerow([
            book['all_time_number'],
            book['yearly_number'],
            book['title'],
            book.get('subtitle', '') or '',
            book['author'],
            book['pages'],
            book['date_begun_date'].strftime('%Y-%m-%d') if book['date_begun_date'] else '',
            book['date_finished_date'].strftime('%Y-%m-%d') if book['date_finished_date'] else '',
            book['total_days'] or '',
            book.get('days_paused', 0) or '',
            book['pages_per_day'] or '',
            rating_labels.get(book['rating'], ''),
            'Yes' if book['did_not_finish'] else '',
            book.get('pages_completed', '') or '',
            book['notes']
        ])
    
    # Generate response
    output.seek(0)
    filename = f"libram-export-{datetime.now().strftime('%Y-%m-%d')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_date_from_form(field_name: str) -> date:
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


def _get_date_options() -> dict:
    """Get date options (kept for backward compatibility)."""
    return {}


def _get_form_context() -> dict:
    """Get common context for book forms including book types and rating names."""
    db = current_app.get_db()
    book_types = db.get_all_book_types()
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
