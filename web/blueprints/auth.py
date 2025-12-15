"""
Libram Authentication Blueprint
Login, logout, and session management.
"""

import time
from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, current_app
from core.fortunes import get_fortune

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login page and authentication."""
    db = current_app.get_db()
    
    # Check if password is set up
    if not db.has_password():
        return redirect(url_for('auth.setup'))
    
    error = None
    timeout = request.args.get('timeout')
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if db.verify_password(password):
            # Clear any stale session data first (fixes Safari/Firefox issue)
            session.clear()
            
            # Set fresh session with last_activity immediately
            session['logged_in'] = True
            session['last_activity'] = time.time()
            session['fortune'] = get_fortune()
            
            # Use make_response for explicit cookie handling
            response = make_response(redirect(url_for('books.index')))
            return response
        else:
            error = 'Invalid password'
    
    return render_template('login.html', error=error, timeout=timeout)


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Initial password setup for new installations."""
    db = current_app.get_db()
    
    # If password already set, redirect to login
    if db.has_password():
        return redirect(url_for('auth.login'))
    
    error = None
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        
        if len(password) < 6:
            error = 'Password must be at least 6 characters'
        elif password != confirm:
            error = 'Passwords do not match'
        else:
            db.set_password(password)
            
            # Log in immediately after setup
            session.clear()
            session['logged_in'] = True
            session['last_activity'] = time.time()
            session['fortune'] = get_fortune()
            
            return redirect(url_for('books.index'))
    
    return render_template('setup.html', error=error)


@auth_bp.route('/logout')
def logout():
    """Log out and clear session."""
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change the master password."""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    db = current_app.get_db()
    error = None
    success = False
    
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        
        if not db.verify_password(current):
            error = 'Current password is incorrect'
        elif len(new_password) < 6:
            error = 'New password must be at least 6 characters'
        elif new_password != confirm:
            error = 'New passwords do not match'
        else:
            db.set_password(new_password)
            success = True
    
    return render_template('change_password.html', error=error, success=success)


# Before request handler for session timeout
@auth_bp.before_app_request
def check_session():
    """Check session validity and timeout."""
    # Skip for static files, login, setup, and logout
    if request.endpoint in (None, 'static', 'auth.login', 'auth.setup', 'auth.logout'):
        return
    
    # Check if logged in
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Check session timeout
    db = current_app.get_db()
    timeout_minutes = int(db.get_setting('session_timeout', '30'))
    
    if timeout_minutes > 0:
        last_activity = session.get('last_activity', 0)
        elapsed = time.time() - last_activity
        
        if elapsed > timeout_minutes * 60:
            session.clear()
            return redirect(url_for('auth.login', timeout=1))
    
    # Update last activity
    session['last_activity'] = time.time()
    
    # Check auto-backup (only once per session, or every hour)
    last_backup_check = session.get('last_backup_check', 0)
    if time.time() - last_backup_check > 3600:  # Check at most once per hour
        session['last_backup_check'] = time.time()
        from web.blueprints.backups import check_auto_backup
        check_auto_backup(current_app)


@auth_bp.after_app_request
def add_no_cache_headers(response):
    """Prevent browser from caching authenticated pages."""
    # Only add no-cache for HTML responses on authenticated routes
    if request.endpoint and request.endpoint not in ('static', 'auth.login', 'auth.setup'):
        if response.content_type and 'text/html' in response.content_type:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    return response
