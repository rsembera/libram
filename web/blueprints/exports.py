"""
Libram Export Blueprint
Export books to various formats.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, Response, current_app

exports_bp = Blueprint('exports', __name__, url_prefix='/export')


@exports_bp.route('/')
def export_page():
    """Show the export options page."""
    return render_template('export.html')


@exports_bp.route('/download', methods=['POST'])
def download():
    """Generate and download export file."""
    db = current_app.get_db()
    
    # Get format and order
    export_format = request.form.get('format', 'csv')
    order = request.form.get('order', 'newest')
    md_style = request.form.get('md_style', 'compact')
    
    # Get date range
    date_from = request.form.get('date_from', '')
    date_to = request.form.get('date_to', '')
    
    # Parse dates
    from_date = None
    to_date = None
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get all books and filter by date range
    books_by_year = db.get_books_by_year()
    all_books = []
    for year, books in books_by_year.items():
        all_books.extend(books)
    
    # Sort by date begun, then by all_time_number for stable ordering
    reverse_order = (order == 'newest')
    all_books.sort(key=lambda b: (b['date_begun'] or 0, b['all_time_number'] or 0), reverse=reverse_order)
    
    # Filter by date range
    if from_date or to_date:
        filtered = []
        for book in all_books:
            if book['date_begun_date']:
                book_date = book['date_begun_date']
                if from_date and book_date < from_date:
                    continue
                if to_date and book_date > to_date:
                    continue
                filtered.append(book)
        all_books = filtered
    
    # Generate export
    if export_format == 'markdown':
        return generate_markdown(all_books, from_date, to_date, order, md_style)
    else:
        return generate_csv(all_books)


def _csv_safe(value):
    """Guard against CSV formula injection in spreadsheet apps.
    
    Cells beginning with =, +, -, @ (or a tab / carriage return) are
    interpreted as formulas by Excel and others. Prefixing with a single
    quote forces them to be treated as plain text.
    """
    if isinstance(value, str) and value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def _pages_read(book) -> int:
    """Pages counted toward totals: full count if finished, pages completed
    if DNF, nothing while still in progress (same rule as the dashboard)."""
    if book['did_not_finish']:
        return book.get('pages_completed') or 0
    return book['pages'] if book['date_finished'] else 0


def _group_by_year(books, order):
    """Group books by the year they were begun. Returns [(year, books), ...]
    with years newest- or oldest-first to match `order`."""
    books_by_year = {}
    for book in books:
        year = book['date_begun_date'].year if book.get('date_begun_date') else 'Unknown'
        books_by_year.setdefault(year, []).append(book)
    
    years = sorted((y for y in books_by_year if isinstance(y, int)), reverse=(order == 'newest'))
    if 'Unknown' in books_by_year:
        years.append('Unknown')
    return [(year, books_by_year[year]) for year in years]


def _md_cell(text) -> str:
    """Make text safe inside a Markdown table cell."""
    return str(text or '').replace('|', '\\|').replace('\r', '').replace('\n', ' ')


def _markdown_response(lines):
    filename = f"libram-export-{date.today().strftime('%Y-%m-%d')}.md"
    return Response(
        '\n'.join(lines),
        mimetype='text/markdown',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


def generate_csv(books):
    """Generate CSV export."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'All-Time #', 'Year #', 'Title', 'Subtitle', 'Author', 'Pages',
        'Date Begun', 'Date Finished', 'Days', 'Days Paused', 'Pages/Day',
        'Rating', 'Did Not Finish', 'Pages Completed', 'Type', 'Notes'
    ])
    
    # Data rows
    for book in books:
        # Rating: blank if 0, otherwise 1-5
        rating = book['rating'] if book['rating'] > 0 else ''
        
        # Pages completed: DNF shows partial, finished shows total, in-progress is blank
        if book['did_not_finish']:
            pages_completed = book.get('pages_completed', '') or ''
        elif book['date_finished']:
            pages_completed = book['pages']
        else:
            pages_completed = ''
        
        writer.writerow([
            book['all_time_number'],
            book['yearly_number'],
            _csv_safe(book['title']),
            _csv_safe(book.get('subtitle', '') or ''),
            _csv_safe(book['author']),
            book['pages'],
            book['date_begun_date'].strftime('%Y-%m-%d') if book['date_begun_date'] else '',
            book['date_finished_date'].strftime('%Y-%m-%d') if book['date_finished_date'] else '',
            book['total_days'] or '',
            book.get('days_paused', 0) or '',
            book['pages_per_day'] or '',
            rating,
            'Yes' if book['did_not_finish'] else '',
            pages_completed,
            _csv_safe(book.get('type_name', '') or ''),
            _csv_safe(book['notes'])
        ])
    
    # Create response
    output.seek(0)
    filename = f"libram-export-{date.today().strftime('%Y-%m-%d')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


def generate_markdown(books, from_date=None, to_date=None, order='newest', style='compact'):
    """Generate Markdown export."""
    lines = []
    
    # Title
    lines.append('# My Reading List')
    lines.append('')
    
    # Date range subtitle
    if from_date or to_date:
        if from_date and to_date:
            lines.append(f'*{from_date.strftime("%B %d, %Y")} – {to_date.strftime("%B %d, %Y")}*')
        elif from_date:
            lines.append(f'*From {from_date.strftime("%B %d, %Y")}*')
        else:
            lines.append(f'*Through {to_date.strftime("%B %d, %Y")}*')
        lines.append('')
    
    # Stats
    total_books = len(books)
    total_pages = sum(_pages_read(book) for book in books)
    lines.append(f'**{total_books} books** · **{total_pages:,} pages**')
    lines.append('')
    lines.append('---')
    lines.append('')
    
    if style == 'detailed':
        return generate_markdown_detailed(books, lines, order)
    else:
        return generate_markdown_compact(books, lines, order)


def generate_markdown_compact(books, lines, order):
    """Generate compact Markdown format (grouped list with notes)."""
    for year, year_books in _group_by_year(books, order):
        lines.append(f'## {year}')
        lines.append('')
        
        for book in year_books:
            # Rating as asterisks or DNF
            rating_str = ''
            if book['did_not_finish']:
                rating_str = ' ❌'
            elif book['rating'] > 0:
                rating_str = ' ' + ('★' * book['rating'])
            
            # Title line: #1 (Yr. #1) · Title (rating at end)
            title_line = f'- **#{book["all_time_number"]} (Yr. #{book["yearly_number"]}) · {book["title"]}**{rating_str}'
            lines.append(title_line)
            
            # Subtitle (if any)
            if book.get('subtitle'):
                lines.append(f'  *{book["subtitle"]}*')
            
            # Author and type
            author_line = f'  {book["author"]}'
            if book.get('type_name'):
                author_line += f' · {book["type_name"]}'
            lines.append(author_line)
            
            # Stats line
            stats = []
            
            # Pages
            if book['pages']:
                if book['did_not_finish'] and book.get('pages_completed'):
                    stats.append(f'{book["pages_completed"]}/{book["pages"]} pages')
                else:
                    stats.append(f'{book["pages"]} pages')
            
            # Days and pace
            if book['total_days']:
                days_str = f'{book["total_days"]} days'
                if book.get('days_paused'):
                    days_str += f' ({book["days_paused"]} paused)'
                stats.append(days_str)
                
                if book['pages_per_day']:
                    stats.append(f'{book["pages_per_day"]} pg/day')
            
            # Dates
            if book['date_begun_date']:
                if book['date_finished_date']:
                    # Same month/year: Dec 05–06, 2025
                    if book['date_begun_date'].strftime('%b %Y') == book['date_finished_date'].strftime('%b %Y'):
                        date_str = f'{book["date_begun_date"].strftime("%b %d")}–{book["date_finished_date"].strftime("%d, %Y")}'
                    else:
                        date_str = f'{book["date_begun_date"].strftime("%b %d, %Y")} – {book["date_finished_date"].strftime("%b %d, %Y")}'
                else:
                    date_str = f'Started {book["date_begun_date"].strftime("%b %d, %Y")}'
                stats.append(date_str)
            
            lines.append(f'  {" · ".join(stats)}')
            
            # Notes (if any). Every line needs the quote marker, or a
            # multi-line note breaks out of the list item.
            if book.get('notes') and book['notes'].strip():
                for note_line in book['notes'].strip().splitlines():
                    lines.append(f'  > {note_line}'.rstrip())
            
            lines.append('')
        
        lines.append('')
    
    return _markdown_response(lines)


def generate_markdown_detailed(books, lines, order):
    """Generate detailed Markdown format (table)."""
    for year, year_books in _group_by_year(books, order):
        lines.append(f'## {year}')
        lines.append('')
        
        # Table header
        lines.append('| # | Title | Author | Type | Pages | Days | Pace | Rating |')
        lines.append('|---|-------|--------|------|------:|-----:|-----:|:------:|')
        
        for book in year_books:
            # Book number
            num = str(book["all_time_number"])
            
            # Title (with subtitle if present)
            title = book['title']
            if book.get('subtitle'):
                title += f': {book["subtitle"]}'
            title = _md_cell(title)
            
            # Author
            author = _md_cell(book['author'])
            
            # Type
            book_type = _md_cell(book.get('type_name'))
            
            # Pages
            if book['did_not_finish'] and book.get('pages_completed'):
                pages = f'{book["pages_completed"]}/{book["pages"]}'
            else:
                pages = str(book['pages']) if book['pages'] else ''
            
            # Days
            days = str(book['total_days']) if book['total_days'] else ''
            
            # Pace
            pace = str(book['pages_per_day']) if book['pages_per_day'] else ''
            
            # Rating
            if book['did_not_finish']:
                rating = 'DNF'
            elif book['rating'] > 0:
                rating = '★' * book['rating']
            else:
                rating = ''
            
            lines.append(f'| {num} | {title} | {author} | {book_type} | {pages} | {days} | {pace} | {rating} |')
        
        lines.append('')
        lines.append('')
    
    return _markdown_response(lines)
