"""
Libram Database Module
SQLite database for book tracking.
"""

import os
import time
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, date


class Database:
    """SQLite database for Libram."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to database file. Defaults to ~/libram/data/libram.db
        """
        if db_path is None:
            db_path = os.path.expanduser('~/libram/data/libram.db')
        
        self.db_path = db_path
        self.conn = None
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    def connect(self):
        """Open database connection."""
        self.conn = sqlite3.connect(self.db_path)
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Run migrations
        self._run_migrations()
        
        return self
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _run_migrations(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                pages INTEGER NOT NULL,
                date_begun INTEGER NOT NULL,
                date_finished INTEGER,
                days_paused INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 0,
                did_not_finish INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                all_time_number INTEGER,
                yearly_number INTEGER,
                created_at INTEGER NOT NULL,
                modified_at INTEGER NOT NULL
            )
        """)
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                modified_at INTEGER NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_date_begun 
            ON books(date_begun)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_books_all_time_number 
            ON books(all_time_number)
        """)
        
        # Migration: Add days_paused column if it doesn't exist
        cursor.execute("PRAGMA table_info(books)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'days_paused' not in columns:
            cursor.execute("ALTER TABLE books ADD COLUMN days_paused INTEGER DEFAULT 0")
        
        # Book Types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL,
                bubble_color TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                modified_at INTEGER NOT NULL
            )
        """)
        
        # Migration: Add type_id column to books if it doesn't exist
        if 'type_id' not in columns:
            cursor.execute("ALTER TABLE books ADD COLUMN type_id INTEGER REFERENCES book_types(id)")
        
        # Migration: Add pages_completed column for DNF books
        if 'pages_completed' not in columns:
            cursor.execute("ALTER TABLE books ADD COLUMN pages_completed INTEGER")
        
        # Migration: Add subtitle column
        if 'subtitle' not in columns:
            cursor.execute("ALTER TABLE books ADD COLUMN subtitle TEXT DEFAULT ''")
        
        # Seed default book types if none exist
        cursor.execute("SELECT COUNT(*) FROM book_types")
        if cursor.fetchone()[0] == 0:
            now = int(time.time())
            cursor.execute("""
                INSERT INTO book_types (name, color, bubble_color, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('Fiction', '#D4C5E0', '#F3EDF7', now, now))
            cursor.execute("""
                INSERT INTO book_types (name, color, bubble_color, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?)
            """, ('Non-Fict', '#9FCFC0', '#E0F2EE', now, now))
        
        self.conn.commit()
    
    # =========================================================================
    # BOOK CRUD OPERATIONS
    # =========================================================================
    
    def add_book(self, title: str, author: str, pages: int, 
                 date_begun: date, date_finished: date = None,
                 days_paused: int = 0, rating: int = 0, 
                 did_not_finish: bool = False, notes: str = '',
                 type_id: int = None, pages_completed: int = None,
                 subtitle: str = '') -> int:
        """
        Add a new book to the database.
        
        Returns:
            The ID of the newly created book.
        """
        cursor = self.conn.cursor()
        now = int(time.time())
        
        # Convert dates to timestamps
        begun_ts = int(datetime.combine(date_begun, datetime.min.time()).timestamp())
        finished_ts = None
        if date_finished:
            finished_ts = int(datetime.combine(date_finished, datetime.min.time()).timestamp())
        
        # Calculate book numbers
        all_time_number = self._get_next_all_time_number()
        yearly_number = self._get_next_yearly_number(date_begun.year)
        
        cursor.execute("""
            INSERT INTO books (
                title, subtitle, author, pages, date_begun, date_finished,
                days_paused, rating, did_not_finish, notes,
                all_time_number, yearly_number,
                type_id, pages_completed, created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, subtitle, author, pages, begun_ts, finished_ts,
            days_paused, rating, 1 if did_not_finish else 0, notes,
            all_time_number, yearly_number,
            type_id, pages_completed, now, now
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_book(self, book_id: int) -> dict:
        """Get a single book by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_book(row, cursor.description)
        return None
    
    def get_all_books(self) -> list:
        """Get all books, ordered by date_begun descending."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT b.*, bt.name as type_name, bt.color as type_color, bt.bubble_color as type_bubble
            FROM books b
            LEFT JOIN book_types bt ON b.type_id = bt.id
            ORDER BY b.date_begun DESC, b.id DESC
        """)
        
        return [self._row_to_book(row, cursor.description) 
                for row in cursor.fetchall()]
    
    def get_books_by_year(self) -> dict:
        """
        Get all books grouped by year (based on date_begun).
        
        Returns:
            Dict with years as keys, list of books as values.
            Years are sorted descending (most recent first).
        """
        books = self.get_all_books()
        
        # Group by year
        by_year = {}
        for book in books:
            year = book['year']
            if year not in by_year:
                by_year[year] = []
            by_year[year].append(book)
        
        # Sort years descending
        return dict(sorted(by_year.items(), reverse=True))
    
    def update_book(self, book_id: int, **kwargs) -> bool:
        """
        Update a book's fields.
        
        Args:
            book_id: The book ID to update.
            **kwargs: Fields to update (title, author, pages, etc.)
        
        Returns:
            True if successful, False if book not found.
        """
        cursor = self.conn.cursor()
        
        # Build UPDATE statement dynamically
        allowed_fields = {
            'title', 'subtitle', 'author', 'pages', 'date_begun', 'date_finished',
            'days_paused', 'rating', 'did_not_finish', 'notes', 'type_id',
            'pages_completed'
        }
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue
            
            # Convert dates to timestamps
            if key in ('date_begun', 'date_finished') and value:
                if isinstance(value, date):
                    value = int(datetime.combine(value, datetime.min.time()).timestamp())
            
            # Convert bool to int
            if key == 'did_not_finish':
                value = 1 if value else 0
            
            updates.append(f"{key} = ?")
            values.append(value)
        
        if not updates:
            return False
        
        # Add modified_at
        updates.append("modified_at = ?")
        values.append(int(time.time()))
        
        # Add book_id for WHERE clause
        values.append(book_id)
        
        cursor.execute(f"""
            UPDATE books 
            SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_book(self, book_id: int) -> bool:
        """Delete a book by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # =========================================================================
    # BOOK TYPE OPERATIONS
    # =========================================================================
    
    def get_all_book_types(self) -> list:
        """Get all book types."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM book_types ORDER BY name")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_book_type(self, type_id: int) -> dict:
        """Get a single book type by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM book_types WHERE id = ?", (type_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def add_book_type(self, name: str, color: str, bubble_color: str) -> int:
        """Add a new book type."""
        cursor = self.conn.cursor()
        now = int(time.time())
        cursor.execute("""
            INSERT INTO book_types (name, color, bubble_color, created_at, modified_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, color, bubble_color, now, now))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_book_type(self, type_id: int, name: str = None, 
                         color: str = None, bubble_color: str = None) -> bool:
        """Update a book type."""
        cursor = self.conn.cursor()
        now = int(time.time())
        
        updates = ['modified_at = ?']
        values = [now]
        
        if name is not None:
            updates.append('name = ?')
            values.append(name)
        if color is not None:
            updates.append('color = ?')
            values.append(color)
        if bubble_color is not None:
            updates.append('bubble_color = ?')
            values.append(bubble_color)
        
        values.append(type_id)
        cursor.execute(f"""
            UPDATE book_types SET {', '.join(updates)} WHERE id = ?
        """, values)
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_book_type(self, type_id: int) -> bool:
        """Delete a book type (only if no books assigned)."""
        cursor = self.conn.cursor()
        # Check if any books use this type
        cursor.execute("SELECT COUNT(*) FROM books WHERE type_id = ?", (type_id,))
        if cursor.fetchone()[0] > 0:
            return False
        # Check if this is the last type
        cursor.execute("SELECT COUNT(*) FROM book_types")
        if cursor.fetchone()[0] <= 1:
            return False
        cursor.execute("DELETE FROM book_types WHERE id = ?", (type_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_books_count_by_type(self, type_id: int) -> int:
        """Get number of books assigned to a type."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books WHERE type_id = ?", (type_id,))
        return cursor.fetchone()[0]

    def get_books_by_type_stats(self, limit: int = 6) -> list:
        """Get book counts by type for chart, ordered by count descending."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT bt.name, bt.color, COUNT(b.id) as book_count
            FROM book_types bt
            LEFT JOIN books b ON b.type_id = bt.id
            GROUP BY bt.id
            ORDER BY book_count DESC
            LIMIT ?
        """, (limit,))
        return [{'name': row[0], 'color': row[1], 'count': row[2]} for row in cursor.fetchall()]

    # =========================================================================
    # SETTINGS
    # =========================================================================
    
    def get_setting(self, key: str, default: str = None) -> str:
        """Get a setting value."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default
    
    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        cursor = self.conn.cursor()
        now = int(time.time())
        
        cursor.execute("""
            INSERT INTO settings (key, value, modified_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, modified_at = ?
        """, (key, value, now, value, now))
        
        self.conn.commit()
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> dict:
        """Get reading statistics for the dashboard."""
        cursor = self.conn.cursor()
        now = int(time.time())
        current_year = datetime.now().year
        
        # Total books
        cursor.execute("SELECT COUNT(*) FROM books")
        total_books = cursor.fetchone()[0]
        
        # Books this year
        year_start = int(datetime(current_year, 1, 1).timestamp())
        cursor.execute("""
            SELECT COUNT(*) FROM books 
            WHERE date_begun >= ?
        """, (year_start,))
        books_this_year = cursor.fetchone()[0]
        
        # Total pages this year (only count completed books or DNF books)
        # In-progress books (no date_finished, not DNF) are not counted
        cursor.execute("""
            SELECT COALESCE(SUM(
                CASE 
                    WHEN did_not_finish = 1 THEN COALESCE(pages_completed, 0)
                    WHEN date_finished IS NOT NULL THEN pages
                    ELSE 0 
                END
            ), 0) FROM books 
            WHERE date_begun >= ?
        """, (year_start,))
        pages_this_year = cursor.fetchone()[0]
        
        # Total pages all time (only count completed books or DNF books)
        cursor.execute("""
            SELECT COALESCE(SUM(
                CASE 
                    WHEN did_not_finish = 1 THEN COALESCE(pages_completed, 0)
                    WHEN date_finished IS NOT NULL THEN pages
                    ELSE 0 
                END
            ), 0) FROM books
        """)
        total_pages = cursor.fetchone()[0]
        
        # Average days to finish (completed books only)
        cursor.execute("""
            SELECT AVG((date_finished - date_begun) / 86400.0 + 1)
            FROM books 
            WHERE date_finished IS NOT NULL AND did_not_finish = 0
        """)
        avg_days = cursor.fetchone()[0]
        avg_days = round(avg_days, 1) if avg_days else 0
        
        # Currently reading (started but not finished)
        cursor.execute("""
            SELECT COUNT(*) FROM books 
            WHERE date_finished IS NULL AND did_not_finish = 0
        """)
        currently_reading = cursor.fetchone()[0]
        
        return {
            'total_books': total_books,
            'books_this_year': books_this_year,
            'pages_this_year': pages_this_year,
            'total_pages': total_pages,
            'avg_days_to_finish': avg_days,
            'currently_reading': currently_reading
        }
    
    def get_books_per_month(self, months: int = 12) -> list:
        """
        Get books finished per month for the last N months.
        
        Args:
            months: Number of months to include (default 12)
            
        Returns:
            List of dicts with 'month', 'year', 'label', and 'count' keys,
            ordered from oldest to newest.
        """
        cursor = self.conn.cursor()
        
        # Calculate the start date (beginning of month, N months ago)
        now = datetime.now()
        
        results = []
        for i in range(months - 1, -1, -1):
            # Calculate month/year for this slot
            month_offset = now.month - 1 - i
            year = now.year + (month_offset // 12)
            month = (month_offset % 12) + 1
            
            # Get timestamp range for this month
            month_start = int(datetime(year, month, 1).timestamp())
            if month == 12:
                month_end = int(datetime(year + 1, 1, 1).timestamp())
            else:
                month_end = int(datetime(year, month + 1, 1).timestamp())
            
            # Count books finished in this month
            cursor.execute("""
                SELECT COUNT(*) FROM books 
                WHERE date_finished >= ? AND date_finished < ?
                AND did_not_finish = 0
            """, (month_start, month_end))
            count = cursor.fetchone()[0]
            
            # Create short month label
            month_label = datetime(year, month, 1).strftime('%b')
            
            results.append({
                'month': month,
                'year': year,
                'label': month_label,
                'count': count
            })
        
        return results
    
    def get_avg_pages_per_day_by_month(self, months: int = 12) -> list:
        """
        Get average pages per day for books finished in each of the last N months.
        
        Args:
            months: Number of months to include (default 12)
            
        Returns:
            List of dicts with 'month', 'year', 'label', and 'avg' keys,
            ordered from oldest to newest.
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        
        results = []
        for i in range(months - 1, -1, -1):
            # Calculate month/year for this slot
            month_offset = now.month - 1 - i
            year = now.year + (month_offset // 12)
            month = (month_offset % 12) + 1
            
            # Get timestamp range for this month
            month_start = int(datetime(year, month, 1).timestamp())
            if month == 12:
                month_end = int(datetime(year + 1, 1, 1).timestamp())
            else:
                month_end = int(datetime(year, month + 1, 1).timestamp())
            
            # Calculate pages_per_day inline: pages / (total_days - days_paused)
            # total_days = (date_finished - date_begun) / 86400 + 1
            cursor.execute("""
                SELECT AVG(
                    CAST(pages AS REAL) / 
                    NULLIF((date_finished - date_begun) / 86400.0 + 1 - COALESCE(days_paused, 0), 0)
                ) FROM books 
                WHERE date_finished >= ? AND date_finished < ?
                AND date_finished IS NOT NULL
                AND did_not_finish = 0
            """, (month_start, month_end))
            avg = cursor.fetchone()[0]
            avg = round(avg, 1) if avg else 0
            
            # Create short month label
            month_label = datetime(year, month, 1).strftime('%b')
            
            results.append({
                'month': month,
                'year': year,
                'label': month_label,
                'avg': avg
            })
        
        return results
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_next_all_time_number(self) -> int:
        """Get the next all-time book number."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(all_time_number) FROM books")
        result = cursor.fetchone()[0]
        return (result or 0) + 1
    
    def _get_next_yearly_number(self, year: int) -> int:
        """Get the next yearly book number for a given year."""
        cursor = self.conn.cursor()
        year_start = int(datetime(year, 1, 1).timestamp())
        year_end = int(datetime(year + 1, 1, 1).timestamp())
        
        cursor.execute("""
            SELECT MAX(yearly_number) FROM books 
            WHERE date_begun >= ? AND date_begun < ?
        """, (year_start, year_end))
        
        result = cursor.fetchone()[0]
        return (result or 0) + 1
    
    def _row_to_book(self, row, description) -> dict:
        """Convert a database row to a book dictionary."""
        columns = [col[0] for col in description]
        book = dict(zip(columns, row))
        
        # Convert timestamps to dates
        if book['date_begun']:
            dt = datetime.fromtimestamp(book['date_begun'])
            book['date_begun_date'] = dt.date()
            book['year'] = dt.year
        
        if book['date_finished']:
            book['date_finished_date'] = datetime.fromtimestamp(
                book['date_finished']
            ).date()
        else:
            book['date_finished_date'] = None
        
        # Calculate derived fields
        if book['date_begun'] and book['date_finished']:
            days = (book['date_finished'] - book['date_begun']) // 86400 + 1
            book['total_days'] = days
            # Calculate active reading days (excluding paused days)
            days_paused = book.get('days_paused', 0) or 0
            active_days = max(1, days - days_paused)
            book['active_days'] = active_days
            # For DNF books, use pages_completed; otherwise use pages
            pages_read = book.get('pages_completed') if book['did_not_finish'] and book.get('pages_completed') else book['pages']
            book['pages_per_day'] = pages_read // active_days if active_days > 0 else 0
        else:
            book['total_days'] = None
            book['active_days'] = None
            book['pages_per_day'] = None
        
        # Convert did_not_finish to bool
        book['did_not_finish'] = bool(book['did_not_finish'])
        
        return book
    
    # =========================================================================
    # PASSWORD MANAGEMENT
    # =========================================================================
    
    def verify_password(self, password: str) -> bool:
        """Verify the master password."""
        stored_hash = self.get_setting('password_hash')
        if not stored_hash:
            return False
        
        # Hash the provided password
        test_hash = hashlib.sha256(password.encode()).hexdigest()
        return test_hash == stored_hash
    
    def set_password(self, password: str):
        """Set or change the master password."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.set_setting('password_hash', password_hash)
    
    def has_password(self) -> bool:
        """Check if a password has been set."""
        return self.get_setting('password_hash') is not None
