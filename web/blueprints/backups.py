"""
Libram Backups Blueprint
Database backup and restore functionality.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, render_template, request, current_app, jsonify, send_file, Flask

backups_bp = Blueprint('backups', __name__)

# App root is parent of 'web/blueprints' directory
APP_ROOT = Path(__file__).parent.parent.parent
BACKUP_DIR = str(APP_ROOT / 'backups')

# Auto-backup frequency options (in hours, 0 = never)
FREQUENCY_OPTIONS = [
    ('0', 'Never'),
    ('24', 'Daily'),
    ('168', 'Weekly'),
    ('720', 'Monthly'),
]

# Retention period options (in days, 0 = always)
RETENTION_OPTIONS = [
    ('7', '7 days'),
    ('14', '14 days'),
    ('30', '30 days'),
    ('90', '90 days'),
    ('0', 'Always'),
]


@backups_bp.route('/')
def backups_page():
    """Display backups page with list of available backups."""
    db = current_app.get_db()
    backups = _get_backup_list()
    
    # Get current settings
    auto_frequency = db.get_setting('backup_frequency', '168')  # Default: Weekly
    retention_days = db.get_setting('backup_retention', '7')    # Default: 7 days
    last_auto_backup = db.get_setting('last_auto_backup', '')
    
    return render_template('backups.html', 
                          backups=backups,
                          auto_frequency=auto_frequency,
                          retention_days=retention_days,
                          last_auto_backup=last_auto_backup,
                          frequency_options=FREQUENCY_OPTIONS,
                          retention_options=RETENTION_OPTIONS)


@backups_bp.route('/create', methods=['POST'])
def create_backup():
    """Create a manual backup."""
    db_path = current_app.config['DATABASE_PATH']
    
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    backup_filename = f'libram_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        return jsonify({'status': 'ok', 'filename': backup_filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backups_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save auto-backup settings."""
    db = current_app.get_db()
    
    frequency = request.form.get('frequency', '0')
    retention = request.form.get('retention', '0')
    
    # Validate
    valid_frequencies = [opt[0] for opt in FREQUENCY_OPTIONS]
    valid_retentions = [opt[0] for opt in RETENTION_OPTIONS]
    
    if frequency in valid_frequencies:
        db.set_setting('backup_frequency', frequency)
    if retention in valid_retentions:
        db.set_setting('backup_retention', retention)
    
    # Run cleanup if retention changed
    if retention != '0':
        _cleanup_old_backups(int(retention))
    
    return jsonify({'status': 'ok'})


def check_auto_backup(app: Flask) -> None:
    """Check if auto-backup is due and create one if needed. Call from before_request."""
    db = app.get_db()
    
    frequency_hours = int(db.get_setting('backup_frequency', '168'))  # Default: Weekly
    if frequency_hours == 0:
        return  # Auto-backup disabled
    
    last_backup_str = db.get_setting('last_auto_backup', '')
    
    # Check if backup is due
    backup_due = False
    if not last_backup_str:
        backup_due = True
    else:
        try:
            last_backup = datetime.fromisoformat(last_backup_str)
            if datetime.now() - last_backup > timedelta(hours=frequency_hours):
                backup_due = True
        except ValueError:
            backup_due = True
    
    if backup_due:
        _create_auto_backup(app, db)


def _create_auto_backup(app, db):
    """Create an automatic backup."""
    db_path = app.config['DATABASE_PATH']
    
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    backup_filename = f'libram_auto_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        db.set_setting('last_auto_backup', datetime.now().isoformat())
        
        # Cleanup old backups (0 = Always keep)
        retention_days = int(db.get_setting('backup_retention', '7'))
        if retention_days > 0:
            _cleanup_old_backups(retention_days)
    except Exception:
        pass  # Silently fail for auto-backups


def _cleanup_old_backups(retention_days):
    """Delete backups older than retention period."""
    if not os.path.exists(BACKUP_DIR):
        return
    
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.db'):
            filepath = os.path.join(BACKUP_DIR, filename)
            file_time = datetime.fromtimestamp(os.stat(filepath).st_mtime)
            if file_time < cutoff:
                try:
                    os.remove(filepath)
                except Exception:
                    pass


@backups_bp.route('/download/<filename>')
def download_backup(filename):
    """Download a backup file."""
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(backup_path):
        return 'Backup not found', 404
    
    return send_file(backup_path, as_attachment=True)


@backups_bp.route('/delete/<filename>', methods=['POST'])
def delete_backup(filename):
    """Delete a backup file."""
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(backup_path):
        return jsonify({'status': 'error', 'message': 'Backup not found'}), 404
    
    try:
        os.remove(backup_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backups_bp.route('/restore/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restore from a backup file."""
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    db_path = current_app.config['DATABASE_PATH']
    
    if not os.path.exists(backup_path):
        return jsonify({'status': 'error', 'message': 'Backup not found'}), 404
    
    try:
        # Create a backup of current database before restoring
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        pre_restore_backup = os.path.join(BACKUP_DIR, f'pre_restore_{timestamp}.db')
        shutil.copy2(db_path, pre_restore_backup)
        
        # Restore the backup
        shutil.copy2(backup_path, db_path)
        
        return jsonify({'status': 'ok', 'message': 'Backup restored successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _get_backup_list() -> list:
    """Get list of backup files with metadata."""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.db'):
            filepath = os.path.join(BACKUP_DIR, filename)
            stat = os.stat(filepath)
            
            backups.append({
                'filename': filename,
                'size': _format_size(stat.st_size),
                'created': datetime.fromtimestamp(stat.st_mtime),
                'created_str': datetime.fromtimestamp(stat.st_mtime).strftime('%b %d, %Y %I:%M %p')
            })
    
    # Sort by date, newest first
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    return backups


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f} MB'
