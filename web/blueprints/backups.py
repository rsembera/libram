"""
Libram Backups Blueprint
Database backup and restore functionality.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, send_file

backups_bp = Blueprint('backups', __name__)

BACKUP_DIR = os.path.expanduser('~/libram/backups')


@backups_bp.route('/')
def backups_page():
    """Display backups page with list of available backups."""
    backups = _get_backup_list()
    
    return render_template('backups.html', backups=backups)


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
