"""
Libram Backups Blueprint
Database and cover image backup/restore functionality.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, current_app, jsonify, send_file

from core import backup

backups_bp = Blueprint('backups', __name__)

# Frequency and retention options for UI
FREQUENCY_OPTIONS = [
    ('startup', 'Every Session'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('manual', 'Manual Only'),
]

RETENTION_OPTIONS = [
    ('1_month', '1 Month'),
    ('6_months', '6 Months'),
    ('1_year', '1 Year'),
    ('forever', 'Forever'),
]


@backups_bp.route('/')
def backups_page():
    """Display backups page with list of available backups."""
    db = current_app.get_db()
    
    # Get restore points (unified view of all backups)
    restore_points = backup.get_restore_points()
    
    # Get backup status
    status = backup.get_backup_status()
    
    # Get current settings
    auto_frequency = db.get_setting('backup_frequency', 'daily')
    retention = db.get_setting('backup_retention', '6_months')
    backup_location = db.get_setting('backup_location', '')
    
    # Detect available cloud folders
    cloud_folders = backup.detect_cloud_folders()
    
    return render_template('backups.html', 
                          restore_points=restore_points,
                          status=status,
                          auto_frequency=auto_frequency,
                          retention=retention,
                          backup_location=backup_location,
                          cloud_folders=cloud_folders,
                          frequency_options=FREQUENCY_OPTIONS,
                          retention_options=RETENTION_OPTIONS)


@backups_bp.route('/create', methods=['POST'])
def create_backup():
    """Create a manual backup."""
    db = current_app.get_db()
    backup_dir = backup.get_backup_dir(db)
    
    try:
        result = backup.create_backup(backup_dir, db)
        if result is None:
            return jsonify({
                'status': 'ok', 
                'message': 'No changes since last backup',
                'no_changes': True
            })
        return jsonify({
            'status': 'ok', 
            'filename': result['filename'],
            'type': result['type'],
            'size': backup.format_size(result['backup_size'])
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backups_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save auto-backup settings."""
    db = current_app.get_db()
    
    frequency = request.form.get('frequency', 'daily')
    retention = request.form.get('retention', '6_months')
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
        cloud_folders = backup.detect_cloud_folders()
        valid_paths = [cf['path'] for cf in cloud_folders]
        if location in valid_paths:
            try:
                os.makedirs(location, exist_ok=True)
                db.set_setting('backup_location', location)
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Cannot create folder: {e}'}), 400
    
    # Run cleanup if retention changed
    if retention != 'forever':
        custom_loc = db.get_setting('backup_location', '')
        backup.cleanup_old_backups(retention, custom_loc if custom_loc else None)
    
    return jsonify({'status': 'ok'})



@backups_bp.route('/download/<filename>')
def download_backup(filename):
    """Download a backup file."""
    db = current_app.get_db()
    
    # Security: ensure filename doesn't contain path traversal
    if '..' in filename or '/' in filename:
        return 'Invalid filename', 400
    
    # Find the backup in manifest to get correct directory
    backups = backup.list_backups()
    backup_info = next((b for b in backups if b['filename'] == filename), None)
    
    if not backup_info:
        return 'Backup not found', 404
    
    backup_path = Path(backup_info['path'])
    
    if not backup_path.exists():
        return 'Backup not found', 404
    
    return send_file(backup_path, as_attachment=True)


@backups_bp.route('/restore/<restore_point_id>', methods=['POST'])
def restore_backup(restore_point_id):
    """Prepare restore from a backup (stages files, requires app restart)."""
    try:
        staging_path = backup.prepare_restore(restore_point_id)
        return jsonify({
            'status': 'ok',
            'message': 'Restore prepared. Restart the application to complete.',
            'staging_path': staging_path,
            'requires_restart': True
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@backups_bp.route('/restore/cancel', methods=['POST'])
def cancel_restore():
    """Cancel a pending restore."""
    if backup.cancel_restore():
        return jsonify({'status': 'ok', 'message': 'Restore cancelled'})
    return jsonify({'status': 'ok', 'message': 'No pending restore'})


@backups_bp.route('/restore/status')
def restore_status():
    """Check if there's a pending restore."""
    pending = backup.check_restore_pending()
    if pending:
        return jsonify({
            'pending': True,
            'restore_point': pending['restore_point_id'],
            'prepared_at': pending['prepared_at']
        })
    return jsonify({'pending': False})


def check_auto_backup(app):
    """
    Check if auto-backup is due and create one if needed.
    Called from logout route.
    """
    db = app.get_db()
    
    frequency = db.get_setting('backup_frequency', 'daily')
    
    # Handle legacy values
    legacy_map = {'0': 'manual', '24': 'daily', '168': 'weekly', '720': 'weekly'}
    if frequency in legacy_map:
        frequency = legacy_map[frequency]
        db.set_setting('backup_frequency', frequency)
    
    if not backup.check_backup_needed(frequency):
        return
    
    backup_dir = backup.get_backup_dir(db)
    
    try:
        result = backup.create_backup(backup_dir, db)
        
        if result:
            db.set_setting('last_auto_backup', datetime.now().isoformat())
            
            # Cleanup old backups
            retention = db.get_setting('backup_retention', '6_months')
            if retention != 'forever':
                custom_loc = db.get_setting('backup_location', '')
                backup.cleanup_old_backups(retention, custom_loc if custom_loc else None)
        
        # Record that we checked (even if no changes)
        backup.record_backup_check()
        
    except Exception:
        pass  # Silently fail for auto-backups
