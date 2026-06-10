"""
Libram Backups Blueprint
Database and cover image backup/restore functionality.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, current_app, jsonify

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
            # Even with no changes, record the check so auto-backup
            # logic stays in sync with the current database hash
            backup.record_backup_state(db)
            return jsonify({
                'status': 'ok', 
                'message': 'No changes since last backup',
                'no_changes': True
            })
        # Record state so logout's auto-backup check doesn't see this
        # freshly backed-up data as "changed" and run a redundant pass
        backup.record_backup_state(db)
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




@backups_bp.route('/restore/<restore_point_id>', methods=['POST'])
def restore_backup(restore_point_id):
    """Restore from a backup immediately."""
    from flask import g
    
    try:
        # Close the current database connection so we can replace the file
        db = g.pop('db', None)
        if db is not None:
            db.close()
        
        # Perform the restore
        result = backup.restore_immediate(restore_point_id)
        
        return jsonify({
            'status': 'ok',
            'message': 'Backup restored successfully. The page will reload.',
            'restored_from': result['restored_from']
        })
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def check_auto_backup(app):
    """
    Check if auto-backup is due and create one if needed.
    Also runs retention cleanup.
    Called from logout route AFTER db.checkpoint().
    """
    db = app.get_db()
    
    # Run retention cleanup (regardless of whether a backup is created)
    try:
        retention = db.get_setting('backup_retention', '6_months')
        if retention != 'forever':
            custom_loc = db.get_setting('backup_location', '')
            backup.cleanup_old_backups(retention, custom_loc if custom_loc else None)
    except Exception:
        pass  # Silently fail for cleanup
    
    # Run auto-backup check
    try:
        backup.check_and_run_auto_backup(db)
    except Exception:
        pass  # Silently fail for auto-backups
