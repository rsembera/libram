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
DEFAULT_BACKUP_DIR = APP_ROOT / 'backups'

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


def detect_cloud_folders():
    """
    Detect available cloud sync folders.
    Returns list of {name, path} dicts.
    """
    home = Path.home()
    cloud_folders = []
    
    # iCloud Drive
    icloud = home / 'Library' / 'Mobile Documents' / 'com~apple~CloudDocs'
    if icloud.exists():
        cloud_folders.append({
            'name': 'iCloud Drive',
            'path': str(icloud / 'Libram Backups')
        })
    
    # Dropbox
    dropbox = home / 'Dropbox'
    if dropbox.exists():
        cloud_folders.append({
            'name': 'Dropbox',
            'path': str(dropbox / 'Libram Backups')
        })
    
    # Google Drive (new location)
    google_drive_new = home / 'Library' / 'CloudStorage'
    if google_drive_new.exists():
        for folder in google_drive_new.iterdir():
            if folder.name.startswith('GoogleDrive'):
                cloud_folders.append({
                    'name': 'Google Drive',
                    'path': str(folder / 'My Drive' / 'Libram Backups')
                })
                break
    
    # Google Drive (old location)
    google_drive_old = home / 'Google Drive'
    if google_drive_old.exists() and not any(c['name'] == 'Google Drive' for c in cloud_folders):
        cloud_folders.append({
            'name': 'Google Drive',
            'path': str(google_drive_old / 'Libram Backups')
        })
    
    # OneDrive
    onedrive = home / 'OneDrive'
    if onedrive.exists():
        cloud_folders.append({
            'name': 'OneDrive',
            'path': str(onedrive / 'Libram Backups')
        })
    
    return cloud_folders


def get_backup_dir(db=None):
    """Get the current backup directory (custom or default)."""
    if db is None:
        return DEFAULT_BACKUP_DIR
    
    custom_location = db.get_setting('backup_location', '')
    if custom_location:
        return Path(custom_location)
    return DEFAULT_BACKUP_DIR


@backups_bp.route('/')
def backups_page():
    """Display backups page with list of available backups."""
    db = current_app.get_db()
    backups = _get_backup_list(db)
    
    # Get current settings
    auto_frequency = db.get_setting('backup_frequency', '168')  # Default: Weekly
    retention_days = db.get_setting('backup_retention', '7')    # Default: 7 days
    last_auto_backup = db.get_setting('last_auto_backup', '')
    backup_location = db.get_setting('backup_location', '')
    
    # Detect available cloud folders
    cloud_folders = detect_cloud_folders()
    
    return render_template('backups.html', 
                          backups=backups,
                          auto_frequency=auto_frequency,
                          retention_days=retention_days,
                          last_auto_backup=last_auto_backup,
                          backup_location=backup_location,
                          cloud_folders=cloud_folders,
                          frequency_options=FREQUENCY_OPTIONS,
                          retention_options=RETENTION_OPTIONS)


@backups_bp.route('/create', methods=['POST'])
def create_backup():
    """Create a manual backup."""
    db = current_app.get_db()
    db_path = current_app.config['DATABASE_PATH']
    backup_dir = get_backup_dir(db)
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    backup_filename = f'libram_backup_{timestamp}.db'
    backup_path = backup_dir / backup_filename
    
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
    location = request.form.get('location', '')
    
    # Validate frequency and retention
    valid_frequencies = [opt[0] for opt in FREQUENCY_OPTIONS]
    valid_retentions = [opt[0] for opt in RETENTION_OPTIONS]
    
    if frequency in valid_frequencies:
        db.set_setting('backup_frequency', frequency)
    if retention in valid_retentions:
        db.set_setting('backup_retention', retention)
    
    # Validate and save location
    if location == 'default' or location == '':
        db.set_setting('backup_location', '')
    else:
        # Verify it's a valid cloud folder path
        cloud_folders = detect_cloud_folders()
        valid_paths = [cf['path'] for cf in cloud_folders]
        if location in valid_paths:
            # Create directory if it doesn't exist
            try:
                os.makedirs(location, exist_ok=True)
                db.set_setting('backup_location', location)
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Cannot create folder: {e}'}), 400
    
    # Run cleanup if retention changed
    if retention != '0':
        _cleanup_old_backups(int(retention), db)
    
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
    backup_dir = get_backup_dir(db)
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    backup_filename = f'libram_auto_{timestamp}.db'
    backup_path = backup_dir / backup_filename
    
    try:
        shutil.copy2(db_path, backup_path)
        db.set_setting('last_auto_backup', datetime.now().isoformat())
        
        # Cleanup old backups (0 = Always keep)
        retention_days = int(db.get_setting('backup_retention', '7'))
        if retention_days > 0:
            _cleanup_old_backups(retention_days, db)
    except Exception:
        pass  # Silently fail for auto-backups


def _cleanup_old_backups(retention_days, db=None):
    """Delete backups older than retention period."""
    backup_dir = get_backup_dir(db)
    
    if not backup_dir.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    for filename in os.listdir(backup_dir):
        if filename.endswith('.db'):
            filepath = backup_dir / filename
            file_time = datetime.fromtimestamp(os.stat(filepath).st_mtime)
            if file_time < cutoff:
                try:
                    os.remove(filepath)
                except Exception:
                    pass


@backups_bp.route('/download/<filename>')
def download_backup(filename):
    """Download a backup file."""
    db = current_app.get_db()
    backup_dir = get_backup_dir(db)
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400
    
    backup_path = backup_dir / filename
    
    if not backup_path.exists():
        return 'Backup not found', 404
    
    return send_file(backup_path, as_attachment=True)


@backups_bp.route('/delete/<filename>', methods=['POST'])
def delete_backup(filename):
    """Delete a backup file."""
    db = current_app.get_db()
    backup_dir = get_backup_dir(db)
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    backup_path = backup_dir / filename
    
    if not backup_path.exists():
        return jsonify({'status': 'error', 'message': 'Backup not found'}), 404
    
    try:
        os.remove(backup_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backups_bp.route('/restore/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restore from a backup file."""
    db = current_app.get_db()
    backup_dir = get_backup_dir(db)
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    backup_path = backup_dir / filename
    db_path = Path(current_app.config['DATABASE_PATH'])
    
    if not backup_path.exists():
        return jsonify({'status': 'error', 'message': 'Backup not found'}), 404
    
    try:
        # Create a backup of current database before restoring
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        pre_restore_backup = backup_dir / f'pre_restore_{timestamp}.db'
        shutil.copy2(db_path, pre_restore_backup)
        
        # Restore the backup
        shutil.copy2(backup_path, db_path)
        
        return jsonify({'status': 'ok', 'message': 'Backup restored successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _get_backup_list(db=None) -> list:
    """Get list of backup files with metadata."""
    backup_dir = get_backup_dir(db)
    
    if not backup_dir.exists():
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.db'):
            filepath = backup_dir / filename
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
