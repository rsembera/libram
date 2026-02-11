"""
Libram Backups Blueprint
Database backup and restore functionality.
"""

from __future__ import annotations

import os
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, render_template, request, current_app, jsonify, send_file, Flask

backups_bp = Blueprint('backups', __name__)

# App root is parent of 'web/blueprints' directory
APP_ROOT = Path(__file__).parent.parent.parent
DEFAULT_BACKUP_DIR = APP_ROOT / 'backups'

# Auto-backup frequency options
FREQUENCY_OPTIONS = [
    ('startup', 'Every Session'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('manual', 'Manual Only'),
]

# Retention period options
RETENTION_OPTIONS = [
    ('1_month', '1 Month'),
    ('6_months', '6 Months'),
    ('1_year', '1 Year'),
    ('forever', 'Forever'),
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
    
    # Dropbox (use Apps folder per Dropbox conventions)
    dropbox = home / 'Dropbox'
    if dropbox.exists():
        cloud_folders.append({
            'name': 'Dropbox',
            'path': str(dropbox / 'Apps' / 'Libram Backups')
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
    auto_frequency = db.get_setting('backup_frequency', 'daily')
    retention = db.get_setting('backup_retention', '1_month')
    last_auto_backup = db.get_setting('last_auto_backup', '')
    backup_location = db.get_setting('backup_location', '')
    
    # Detect available cloud folders
    cloud_folders = detect_cloud_folders()
    
    return render_template('backups.html', 
                          backups=backups,
                          auto_frequency=auto_frequency,
                          retention=retention,
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
        # Checkpoint WAL to ensure backup has all data
        db.checkpoint()
        shutil.copy2(db_path, backup_path)
        return jsonify({'status': 'ok', 'filename': backup_filename})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backups_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save auto-backup settings."""
    db = current_app.get_db()
    
    frequency = request.form.get('frequency', 'manual')
    retention = request.form.get('retention', '1_month')
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
    if retention != 'forever':
        _cleanup_old_backups(retention, db)
    
    return jsonify({'status': 'ok'})

def _get_backup_state_file(app):
    """Get path to backup state file (stored outside the database)."""
    db_path = Path(app.config['DATABASE_PATH'])
    return db_path.parent / '.backup_state.json'


def _read_backup_state(app):
    """Read backup state from external JSON file."""
    state_file = _get_backup_state_file(app)
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_backup_state(app, state):
    """Write backup state to external JSON file."""
    state_file = _get_backup_state_file(app)
    with open(state_file, 'w') as f:
        json.dump(state, f)


def _get_db_hash(db_path):
    """Calculate SHA-256 hash of the database file."""
    sha256 = hashlib.sha256()
    with open(db_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_auto_backup(app: Flask) -> None:
    """
    Check if auto-backup is due and create one if needed.
    Called from logout route after WAL checkpoint.
    
    Uses the EdgeCase pattern: all change-detection state lives in an
    external JSON file, never in the database itself. Change detection
    uses SHA-256 hash comparison.
    """
    db = app.get_db()
    
    frequency = db.get_setting('backup_frequency', 'daily')
    
    # Handle legacy values from old hour-based system
    legacy_map = {'0': 'manual', '24': 'daily', '168': 'weekly', '720': 'weekly'}
    if frequency in legacy_map:
        frequency = legacy_map[frequency]
        db.set_setting('backup_frequency', frequency)
    
    if frequency not in ('startup', 'daily', 'weekly', 'manual'):
        frequency = 'daily'
    
    if frequency == 'manual':
        return
    
    state = _read_backup_state(app)
    
    # Check if backup is due based on frequency
    backup_due = False
    last_check = state.get('last_backup_check')
    
    if frequency == 'startup':
        backup_due = True
    elif not last_check:
        backup_due = True
    else:
        try:
            last_check_date = datetime.fromisoformat(last_check).date()
            today = datetime.now().date()
            
            if frequency == 'daily':
                backup_due = today > last_check_date
            elif frequency == 'weekly':
                backup_due = (today - last_check_date).days >= 7
        except ValueError:
            backup_due = True
    
    if not backup_due:
        return
    
    # Check if data actually changed (hash comparison)
    db_path = Path(app.config['DATABASE_PATH'])
    try:
        current_hash = _get_db_hash(db_path)
    except OSError:
        return
    
    last_hash = state.get('last_backup_hash')
    
    if current_hash == last_hash:
        # No changes - just record that we checked
        state['last_backup_check'] = datetime.now().isoformat()
        _write_backup_state(app, state)
        return
    
    # Data changed and backup is due
    _create_auto_backup(app, db)


def _create_auto_backup(app, db):
    """Create an automatic backup and record state."""
    db_path = app.config['DATABASE_PATH']
    backup_dir = get_backup_dir(db)
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    backup_filename = f'libram_auto_{timestamp}.db'
    backup_path = backup_dir / backup_filename
    
    try:
        shutil.copy2(db_path, backup_path)
        db.set_setting('last_auto_backup', datetime.now().isoformat())
        
        # Cleanup old backups
        retention = db.get_setting('backup_retention', '1_month')
        if retention != 'forever':
            _cleanup_old_backups(retention, db)
        
        # Checkpoint to flush set_setting writes from WAL to main db file,
        # then hash so stored hash matches what we'll see next time
        db.checkpoint()
        final_hash = _get_db_hash(db_path)
        _write_backup_state(app, {
            'last_backup_hash': final_hash,
            'last_backup_check': datetime.now().isoformat()
        })
    except Exception:
        pass  # Silently fail for auto-backups


def _cleanup_old_backups(retention, db=None):
    """Delete backups older than retention period.
    
    Args:
        retention: String value - '1_month', '6_months', '1_year', or 'forever'
    """
    if retention == 'forever':
        return
    
    # Convert retention to days
    retention_days = {
        '1_month': 30,
        '6_months': 180,
        '1_year': 365
    }.get(retention, 30)  # Default to 30 days
    
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


def _get_backup_path(filename, location):
    """Get the full path for a backup file given its location."""
    if location == 'default' or not location:
        return DEFAULT_BACKUP_DIR / filename
    return Path(location) / filename


@backups_bp.route('/download/<filename>')
def download_backup(filename):
    """Download a backup file."""
    location = request.args.get('location', 'default')
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400
    
    backup_path = _get_backup_path(filename, location)
    
    if not backup_path.exists():
        return 'Backup not found', 404
    
    return send_file(backup_path, as_attachment=True)


@backups_bp.route('/delete/<filename>', methods=['POST'])
def delete_backup(filename):
    """Delete a backup file."""
    location = request.form.get('location', 'default')
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    backup_path = _get_backup_path(filename, location)
    
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
    location = request.form.get('location', 'default')
    backup_dir = get_backup_dir(db)  # Where to save pre-restore backup
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
    
    backup_path = _get_backup_path(filename, location)
    db_path = Path(current_app.config['DATABASE_PATH'])
    
    if not backup_path.exists():
        return jsonify({'status': 'error', 'message': 'Backup not found'}), 404
    
    try:
        # Create a backup of current database before restoring
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        pre_restore_backup = backup_dir / f'pre_restore_{timestamp}.db'
        shutil.copy2(db_path, pre_restore_backup)
        
        # Restore the backup
        shutil.copy2(backup_path, db_path)
        
        return jsonify({'status': 'ok', 'message': 'Backup restored successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _get_backup_list(db=None) -> list:
    """Get list of backup files with metadata from all locations."""
    backups = []
    scanned_dirs = set()
    
    # Always scan default location
    if DEFAULT_BACKUP_DIR.exists():
        scanned_dirs.add(str(DEFAULT_BACKUP_DIR))
        for filename in os.listdir(DEFAULT_BACKUP_DIR):
            if filename.endswith('.db'):
                filepath = DEFAULT_BACKUP_DIR / filename
                stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': _format_size(stat.st_size),
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'created_str': datetime.fromtimestamp(stat.st_mtime).strftime('%b %d, %Y %I:%M %p'),
                    'location': 'default',
                    'location_name': 'App folder'
                })
    
    # Scan all cloud folders that exist
    for folder in detect_cloud_folders():
        folder_path = Path(folder['path'])
        if folder_path.exists() and str(folder_path) not in scanned_dirs:
            scanned_dirs.add(str(folder_path))
            for filename in os.listdir(folder_path):
                if filename.endswith('.db'):
                    filepath = folder_path / filename
                    stat = os.stat(filepath)
                    backups.append({
                        'filename': filename,
                        'size': _format_size(stat.st_size),
                        'created': datetime.fromtimestamp(stat.st_mtime),
                        'created_str': datetime.fromtimestamp(stat.st_mtime).strftime('%b %d, %Y %I:%M %p'),
                        'location': folder['path'],
                        'location_name': folder['name']
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
