"""
Libram Backup System
Handles full and incremental backups with cover images.

User-facing simplification:
- Single "Backup Now" button (system auto-decides full vs incremental)
- All backups are valid restore points
- No exposed complexity about backup chains

Backup contents:
- data/libram.db (database)
- data/.secret_key (if exists)
- covers/ (cover images)
- covers/thumbs/ (thumbnails)
"""

from __future__ import annotations

import os
import json
import hashlib
import zipfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# App root is parent of 'core' directory
APP_ROOT = Path(__file__).parent.parent
DATA_DIR = APP_ROOT / 'data'
COVERS_DIR = APP_ROOT / 'covers'
BACKUPS_DIR = APP_ROOT / 'backups'
RESTORE_STAGING_DIR = APP_ROOT / '.restore_staging'
MANIFEST_FILE = BACKUPS_DIR / 'manifest.json'


def ensure_backup_dir():
    """Create backups directory if it doesn't exist."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def get_file_hash(filepath):
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_all_backup_files():
    """
    Get list of all files that should be backed up.
    Returns dict: {relative_path: absolute_path}
    """
    files = {}
    
    # Database
    db_path = DATA_DIR / 'libram.db'
    if db_path.exists():
        files['data/libram.db'] = db_path
    
    # Secret key (essential for session security)
    secret_key_path = DATA_DIR / '.secret_key'
    if secret_key_path.exists():
        files['data/.secret_key'] = secret_key_path
    
    # Cover images
    if COVERS_DIR.exists():
        for filepath in COVERS_DIR.rglob('*'):
            if filepath.is_file() and not filepath.name.startswith('.'):
                rel_path = filepath.relative_to(APP_ROOT)
                files[str(rel_path)] = filepath
    
    return files


def get_file_hashes():
    """
    Calculate hashes for all backup files.
    Returns dict: {relative_path: hash}
    """
    files = get_all_backup_files()
    hashes = {}
    for rel_path, abs_path in files.items():
        hashes[rel_path] = get_file_hash(abs_path)
    return hashes


def load_manifest():
    """Load backup manifest from disk."""
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            # Manifest corrupted - backup the bad file and start fresh
            corrupted_path = MANIFEST_FILE.with_suffix('.json.corrupted')
            shutil.copy(MANIFEST_FILE, corrupted_path)
    return {
        'backups': [],
        'last_full_hashes': {},
        'current_chain_id': None,
        'last_backup_check': None
    }


def save_manifest(manifest):
    """Save backup manifest to disk."""
    ensure_backup_dir()
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)


def generate_backup_filename(backup_type):
    """Generate unique backup filename."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    return f"libram_{backup_type}_{timestamp}.zip"


def validate_backup_location(backup_dir):
    """
    Validate that backup location is accessible and writable.
    Returns (success, error_message) tuple.
    """
    backup_dir = Path(backup_dir)
    
    # Check if it's a cloud folder
    cloud_indicators = ['iCloud', 'CloudDocs', 'Dropbox', 'Google Drive', 'OneDrive', 'CloudStorage']
    is_cloud = any(indicator in str(backup_dir) for indicator in cloud_indicators)
    
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to write a test file
        test_file = backup_dir / '.write_test'
        try:
            test_file.write_text('test')
            test_file.unlink()
        except PermissionError:
            if is_cloud:
                return False, "Cannot write to cloud folder. Please check that the cloud service is running and you're signed in."
            return False, "Permission denied. Cannot write to this location."
        except OSError as e:
            if is_cloud:
                return False, f"Cloud folder not accessible. Please check your internet connection."
            return False, f"Cannot write to backup location: {e}"
        
        return True, None
        
    except PermissionError:
        if is_cloud:
            return False, "Cannot access cloud folder. Please check that the cloud service is running and you're signed in."
        return False, "Permission denied. Cannot access this location."
    except OSError as e:
        if is_cloud:
            return False, "Cloud folder not accessible. Please check your internet connection."
        return False, f"Cannot access backup location: {e}"



def create_backup(backup_dir=None, db=None):
    """
    Create a backup, automatically deciding between full and incremental.
    
    Decision logic:
    - No previous backups → full
    - Last full backup > 7 days old → full
    - Otherwise → incremental (only changed files)
    
    Args:
        backup_dir: Optional custom backup directory (for cloud folders)
        db: Optional database instance for checkpointing
    
    Returns:
        dict with backup info, or None if no changes (for incremental)
    """
    manifest = load_manifest()
    
    # Decide: full or incremental?
    need_full = False
    
    if not manifest['backups']:
        need_full = True
    elif not manifest['last_full_hashes']:
        need_full = True
    else:
        # Check age of last full backup (calendar days)
        full_backups = [b for b in manifest['backups'] if b['type'] == 'full']
        if full_backups:
            last_full = max(full_backups, key=lambda x: x['created_at'])
            last_full_date = datetime.fromisoformat(last_full['created_at']).date()
            if (datetime.now().date() - last_full_date).days >= 7:
                need_full = True
        else:
            need_full = True
    
    if need_full:
        return create_full_backup(backup_dir, db)
    else:
        return create_incremental_backup(backup_dir, db)


def create_full_backup(backup_dir=None, db=None):
    """
    Create a full backup of all data.
    
    Args:
        backup_dir: Optional custom backup directory
        db: Optional database instance for checkpointing
    
    Returns:
        dict with backup info or raises exception
    """
    if backup_dir is None:
        backup_dir = BACKUPS_DIR
    else:
        backup_dir = Path(backup_dir)
    
    # Validate location before starting
    valid, error = validate_backup_location(backup_dir)
    if not valid:
        raise ValueError(error)
    
    # Checkpoint WAL to ensure all data is in main db file
    if db:
        db.checkpoint()
    
    filename = generate_backup_filename('full')
    backup_path = backup_dir / filename
    
    files = get_all_backup_files()
    if not files:
        raise ValueError("No files to backup")
    
    # Calculate hashes and create zip
    hashes = {}
    total_size = 0
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for rel_path, abs_path in files.items():
                zf.write(abs_path, rel_path)
                hashes[rel_path] = get_file_hash(abs_path)
                total_size += abs_path.stat().st_size
    except OSError as e:
        if backup_path.exists():
            backup_path.unlink()
        raise ValueError(f"Failed to create backup: {e}")
    
    # Verify backup
    verify_backup(backup_path)
    
    # Update manifest
    manifest = load_manifest()
    chain_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    backup_info = {
        'filename': filename,
        'type': 'full',
        'chain_id': chain_id,
        'created_at': datetime.now().isoformat(),
        'file_count': len(files),
        'original_size': total_size,
        'backup_size': backup_path.stat().st_size,
        'backup_dir': str(backup_dir)
    }
    
    manifest['backups'].append(backup_info)
    manifest['last_full_hashes'] = hashes
    manifest['current_chain_id'] = chain_id
    save_manifest(manifest)
    
    return backup_info


def create_incremental_backup(backup_dir=None, db=None):
    """
    Create an incremental backup (only changed files since last backup).
    
    Args:
        backup_dir: Optional custom backup directory
        db: Optional database instance for checkpointing
    
    Returns:
        dict with backup info, or None if no changes
    """
    manifest = load_manifest()
    
    if not manifest['last_full_hashes']:
        return create_full_backup(backup_dir, db)
    
    if backup_dir is None:
        backup_dir = BACKUPS_DIR
    else:
        backup_dir = Path(backup_dir)
    
    # Validate location
    valid, error = validate_backup_location(backup_dir)
    if not valid:
        raise ValueError(error)
    
    # Checkpoint WAL
    if db:
        db.checkpoint()
    
    # Get current state
    current_hashes = get_file_hashes()
    previous_hashes = manifest['last_full_hashes']
    
    # Find changes
    changed_files = {}
    files = get_all_backup_files()
    
    for rel_path, current_hash in current_hashes.items():
        if rel_path not in previous_hashes or previous_hashes[rel_path] != current_hash:
            changed_files[rel_path] = files[rel_path]
    
    # Check for deleted files
    deleted_files = [p for p in previous_hashes if p not in current_hashes]
    
    if not changed_files and not deleted_files:
        return None  # No changes
    
    filename = generate_backup_filename('incr')
    backup_path = backup_dir / filename
    
    total_size = 0
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for rel_path, abs_path in changed_files.items():
                zf.write(abs_path, rel_path)
                total_size += abs_path.stat().st_size
            
            # Include metadata about deleted files
            if deleted_files:
                metadata = {'deleted_files': deleted_files}
                zf.writestr('_backup_metadata.json', json.dumps(metadata))
    except OSError as e:
        if backup_path.exists():
            backup_path.unlink()
        raise ValueError(f"Failed to create backup: {e}")
    
    # Verify backup
    verify_backup(backup_path)
    
    # Update manifest
    backup_info = {
        'filename': filename,
        'type': 'incremental',
        'chain_id': manifest['current_chain_id'],
        'created_at': datetime.now().isoformat(),
        'file_count': len(changed_files),
        'deleted_count': len(deleted_files),
        'original_size': total_size,
        'backup_size': backup_path.stat().st_size,
        'backup_dir': str(backup_dir)
    }
    
    manifest['backups'].append(backup_info)
    manifest['last_full_hashes'] = current_hashes
    save_manifest(manifest)
    
    return backup_info


def verify_backup(backup_path):
    """
    Verify backup zip integrity.
    Raises exception if corrupted.
    """
    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            bad_file = zf.testzip()
            if bad_file:
                os.remove(backup_path)
                raise ValueError(f"Backup verification failed: {bad_file} is corrupted")
    except zipfile.BadZipFile:
        os.remove(backup_path)
        raise ValueError("Backup file is corrupted")



def list_backups():
    """
    List all available backups with details.
    Returns list sorted by date (newest first).
    """
    manifest = load_manifest()
    backups = []
    
    for backup in manifest['backups']:
        backup_dir = Path(backup.get('backup_dir', BACKUPS_DIR))
        backup_path = backup_dir / backup['filename']
        
        if backup_path.exists():
            backups.append({
                'filename': backup['filename'],
                'type': backup['type'],
                'chain_id': backup['chain_id'],
                'created_at': backup['created_at'],
                'file_count': backup['file_count'],
                'backup_size': backup['backup_size'],
                'backup_size_formatted': format_size(backup['backup_size']),
                'path': str(backup_path),
                'backup_dir': str(backup_dir)
            })
    
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return backups


def get_restore_points():
    """
    Get available restore points.
    
    ALL backups are valid restore points:
    - Full backups restore directly
    - Incremental backups restore by applying chain (full + incrementals)
    - Pre-restore backups are also valid restore points
    
    Returns list of restore points with display info.
    """
    manifest = load_manifest()
    backups = manifest['backups']
    
    # Group by chain
    chains = {}
    for backup in backups:
        chain_id = backup['chain_id']
        if chain_id not in chains:
            chains[chain_id] = {'full': None, 'incrementals': [], 'pre_restore': None}
        
        if backup['type'] == 'full':
            chains[chain_id]['full'] = backup
        elif backup['type'] == 'pre_restore':
            chains[chain_id]['pre_restore'] = backup
        else:
            chains[chain_id]['incrementals'].append(backup)
    
    restore_points = []
    
    for chain_id, chain in chains.items():
        # Handle pre_restore backups (standalone)
        if chain_id == 'pre_restore' and chain.get('pre_restore'):
            backup = chain['pre_restore']
            backup_path = Path(backup.get('backup_dir', BACKUPS_DIR)) / backup['filename']
            if backup_path.exists():
                created = datetime.fromisoformat(backup['created_at'])
                display_time = created.strftime('%b %d, %Y at %I:%M %p').replace(' 0', ' ')
                
                restore_points.append({
                    'id': f"pre_restore_{backup['filename']}",
                    'filename': backup['filename'],
                    'display_name': f"{display_time} (Safety backup)",
                    'created_at': backup['created_at'],
                    'type': 'pre_restore',
                    'is_safety': True,
                    'chain_id': 'pre_restore',
                    'dependent_count': 0,
                    'files_needed': [str(backup_path)]
                })
            continue
        
        if not chain['full']:
            continue  # Skip orphaned incrementals
        
        # Sort incrementals by date
        chain['incrementals'].sort(key=lambda x: x['created_at'])
        
        dependent_count = len(chain['incrementals'])
        
        # Full backup as restore point
        full_backup = chain['full']
        backup_path = Path(full_backup.get('backup_dir', BACKUPS_DIR)) / full_backup['filename']
        
        if backup_path.exists():
            created = datetime.fromisoformat(full_backup['created_at'])
            display_time = created.strftime('%b %d, %Y at %I:%M %p').replace(' 0', ' ')
            
            restore_points.append({
                'id': f"{chain_id}_full",
                'filename': full_backup['filename'],
                'display_name': display_time,
                'created_at': full_backup['created_at'],
                'type': 'full',
                'is_safety': False,
                'chain_id': chain_id,
                'dependent_count': dependent_count,
                'files_needed': [str(backup_path)]
            })
        
        # Each incremental is also a restore point
        files_needed = [str(backup_path)]
        for i, incr in enumerate(chain['incrementals']):
            incr_path = Path(incr.get('backup_dir', BACKUPS_DIR)) / incr['filename']
            if incr_path.exists():
                files_needed = files_needed + [str(incr_path)]
                
                created = datetime.fromisoformat(incr['created_at'])
                display_time = created.strftime('%b %d, %Y at %I:%M %p').replace(' 0', ' ')
                
                restore_points.append({
                    'id': f"{chain_id}_incr_{i}",
                    'filename': incr['filename'],
                    'display_name': display_time,
                    'created_at': incr['created_at'],
                    'type': 'incremental',
                    'is_safety': False,
                    'chain_id': chain_id,
                    'dependent_count': 0,
                    'files_needed': files_needed.copy()
                })
    
    restore_points.sort(key=lambda x: x['created_at'], reverse=True)
    return restore_points



def prepare_restore(restore_point_id):
    """
    Prepare for restore by extracting to staging folder.
    Does NOT replace production files yet.
    
    Returns path to staging folder.
    """
    restore_points = get_restore_points()
    point = next((p for p in restore_points if p['id'] == restore_point_id), None)
    
    if not point:
        raise ValueError(f"Restore point not found: {restore_point_id}")
    
    # Create pre-restore backup first (safety net)
    create_pre_restore_backup()
    
    # Clear any existing staging
    if RESTORE_STAGING_DIR.exists():
        shutil.rmtree(RESTORE_STAGING_DIR)
    
    RESTORE_STAGING_DIR.mkdir(parents=True)
    
    # Track deleted files across incrementals
    deleted_files = set()
    
    # Extract backups in order (full first, then incrementals)
    for backup_path in point['files_needed']:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            # Check for metadata about deleted files
            if '_backup_metadata.json' in zf.namelist():
                metadata = json.loads(zf.read('_backup_metadata.json'))
                deleted_files.update(metadata.get('deleted_files', []))
            
            # Extract all other files (overwrites previous versions)
            for name in zf.namelist():
                if name != '_backup_metadata.json':
                    zf.extract(name, RESTORE_STAGING_DIR)
    
    # Remove files that were deleted in later backups
    for rel_path in deleted_files:
        staged_path = RESTORE_STAGING_DIR / rel_path
        if staged_path.exists():
            staged_path.unlink()
    
    # Write restore marker
    marker = {
        'restore_point_id': restore_point_id,
        'prepared_at': datetime.now().isoformat(),
        'point_info': point
    }
    with open(RESTORE_STAGING_DIR / '.restore_marker', 'w') as f:
        json.dump(marker, f)
    
    return str(RESTORE_STAGING_DIR)


def create_pre_restore_backup():
    """Create a backup of current state before restore (safety net)."""
    ensure_backup_dir()
    
    filename = f"libram_pre_restore_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.zip"
    backup_path = BACKUPS_DIR / filename
    
    files = get_all_backup_files()
    if not files:
        return None
    
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_path, abs_path in files.items():
            zf.write(abs_path, rel_path)
    
    verify_backup(backup_path)
    
    # Add to manifest
    manifest = load_manifest()
    manifest['backups'].append({
        'filename': filename,
        'type': 'pre_restore',
        'chain_id': 'pre_restore',
        'created_at': datetime.now().isoformat(),
        'file_count': len(files),
        'backup_size': backup_path.stat().st_size,
        'backup_dir': str(BACKUPS_DIR)
    })
    save_manifest(manifest)
    
    return str(backup_path)


def restore_immediate(restore_point_id):
    """
    Restore from a backup immediately.
    
    This creates a pre-restore safety backup, then extracts and applies
    the backup directly without requiring an app restart.
    
    Args:
        restore_point_id: The ID of the restore point to restore from
        
    Returns:
        dict with restore info
        
    Raises:
        ValueError: If restore point not found
    """
    restore_points = get_restore_points()
    point = next((p for p in restore_points if p['id'] == restore_point_id), None)
    
    if not point:
        raise ValueError(f"Restore point not found: {restore_point_id}")
    
    # Create pre-restore backup first (safety net)
    create_pre_restore_backup()
    
    # Use a temporary staging directory
    import tempfile
    with tempfile.TemporaryDirectory() as staging_dir:
        staging_path = Path(staging_dir)
        
        # Track deleted files across incrementals
        deleted_files = set()
        
        # Extract backups in order (full first, then incrementals)
        for backup_path in point['files_needed']:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                # Check for metadata about deleted files
                if '_backup_metadata.json' in zf.namelist():
                    metadata = json.loads(zf.read('_backup_metadata.json'))
                    deleted_files.update(metadata.get('deleted_files', []))
                
                # Extract all other files
                for name in zf.namelist():
                    if name != '_backup_metadata.json':
                        zf.extract(name, staging_path)
        
        # Remove files that were deleted in later backups
        for rel_path in deleted_files:
            staged_file = staging_path / rel_path
            if staged_file.exists():
                staged_file.unlink()
        
        # Now apply the restore
        # Replace database
        staged_db = staging_path / 'data' / 'libram.db'
        if staged_db.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            target_db = DATA_DIR / 'libram.db'
            if target_db.exists():
                target_db.unlink()
            shutil.copy2(staged_db, target_db)
        
        # Replace secret key if present
        staged_key = staging_path / 'data' / '.secret_key'
        if staged_key.exists():
            target_key = DATA_DIR / '.secret_key'
            if target_key.exists():
                target_key.unlink()
            shutil.copy2(staged_key, target_key)
        
        # Replace covers
        staged_covers = staging_path / 'covers'
        if staged_covers.exists():
            if COVERS_DIR.exists():
                shutil.rmtree(COVERS_DIR)
            shutil.copytree(staged_covers, COVERS_DIR)
    
    return {
        'restored_at': datetime.now().isoformat(),
        'restored_from': point['display_name'],
        'restore_point_id': restore_point_id
    }


def check_restore_pending():
    """Check if there's a pending restore to complete."""
    marker_path = RESTORE_STAGING_DIR / '.restore_marker'
    if marker_path.exists():
        with open(marker_path, 'r') as f:
            return json.load(f)
    return None


def complete_restore():
    """
    Complete a pending restore by replacing production files.
    Should be called at startup before database is opened.
    
    Returns dict with restore info or None if no restore pending.
    """
    marker = check_restore_pending()
    if not marker:
        return None
    
    # Replace database
    staged_db = RESTORE_STAGING_DIR / 'data' / 'libram.db'
    if staged_db.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        target_db = DATA_DIR / 'libram.db'
        if target_db.exists():
            target_db.unlink()
        shutil.copy2(staged_db, target_db)
    
    # Replace secret key if present
    staged_key = RESTORE_STAGING_DIR / 'data' / '.secret_key'
    if staged_key.exists():
        target_key = DATA_DIR / '.secret_key'
        if target_key.exists():
            target_key.unlink()
        shutil.copy2(staged_key, target_key)
    
    # Replace covers
    staged_covers = RESTORE_STAGING_DIR / 'covers'
    if staged_covers.exists():
        if COVERS_DIR.exists():
            shutil.rmtree(COVERS_DIR)
        shutil.copytree(staged_covers, COVERS_DIR)
    
    # Clean up staging
    shutil.rmtree(RESTORE_STAGING_DIR)
    
    return {
        'restored_at': datetime.now().isoformat(),
        'restore_point': marker['restore_point_id'],
        'original_date': marker['point_info']['created_at']
    }


def cancel_restore():
    """Cancel a pending restore (remove staging folder)."""
    if RESTORE_STAGING_DIR.exists():
        shutil.rmtree(RESTORE_STAGING_DIR)
        return True
    return False




def cleanup_old_backups(retention, custom_location=None):
    """
    Delete backups older than the retention period.
    
    Retention periods:
    - '1_month': 30 days
    - '6_months': 180 days  
    - '1_year': 365 days
    - 'forever': no deletion
    
    Rules:
    - Always keep at least one valid restore point
    - Delete entire chains when their newest incremental exceeds retention
    - Only delete if a newer chain exists
    """
    if retention == 'forever':
        return
    
    retention_days = {
        '1_month': 30,
        '6_months': 180,
        '1_year': 365
    }.get(retention)
    
    if not retention_days:
        return
    
    manifest = load_manifest()
    backup_dir = Path(custom_location) if custom_location else BACKUPS_DIR
    
    cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
    
    # Group backups by chain
    chains = {}
    safety_backups = []
    for backup in manifest['backups']:
        if backup['type'] == 'pre_restore':
            safety_backups.append(backup)
            continue
        chain_id = backup.get('chain_id')
        if chain_id:
            if chain_id not in chains:
                chains[chain_id] = {'full': None, 'incrementals': []}
            if backup['type'] == 'full':
                chains[chain_id]['full'] = backup
            else:
                chains[chain_id]['incrementals'].append(backup)
    
    sorted_chain_ids = sorted(chains.keys(), 
                              key=lambda cid: chains[cid]['full']['created_at'] if chains[cid]['full'] else '')
    
    if len(sorted_chain_ids) <= 1:
        return  # Keep at least one chain
    
    chains_to_delete = []
    
    for chain_id in sorted_chain_ids[:-1]:
        chain = chains[chain_id]
        if not chain['full']:
            continue
        
        all_in_chain = [chain['full']] + chain['incrementals']
        newest_date = max(b['created_at'] for b in all_in_chain)
        
        if newest_date < cutoff_date:
            chains_to_delete.append(chain_id)
    
    for chain_id in chains_to_delete:
        chain = chains[chain_id]
        
        for incr in chain['incrementals']:
            incr_path = Path(incr.get('backup_dir', backup_dir)) / incr['filename']
            if incr_path.exists():
                incr_path.unlink()
            if incr in manifest['backups']:
                manifest['backups'].remove(incr)
        
        if chain['full']:
            full_path = Path(chain['full'].get('backup_dir', backup_dir)) / chain['full']['filename']
            if full_path.exists():
                full_path.unlink()
            if chain['full'] in manifest['backups']:
                manifest['backups'].remove(chain['full'])
    
    # Clean up old safety backups
    for backup in safety_backups:
        if backup['created_at'] < cutoff_date:
            backup_path = Path(backup.get('backup_dir', backup_dir)) / backup['filename']
            if backup_path.exists():
                backup_path.unlink()
            if backup in manifest['backups']:
                manifest['backups'].remove(backup)
    
    if chains_to_delete or safety_backups:
        save_manifest(manifest)


# ============================================================================
# BACKUP STATE (external file to avoid database modification issues)
# ============================================================================

def _get_backup_state_file():
    """Get path to backup state file (stored outside the database)."""
    return DATA_DIR / '.backup_state.json'


def _read_backup_state():
    """Read backup state from external JSON file."""
    state_file = _get_backup_state_file()
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_backup_state(state):
    """Write backup state to external JSON file."""
    state_file = _get_backup_state_file()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(state, f)


def _get_db_hash():
    """Calculate SHA-256 hash of the database file."""
    db_path = DATA_DIR / 'libram.db'
    if not db_path.exists():
        return None
    sha256 = hashlib.sha256()
    with open(db_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_and_run_auto_backup(db, backup_dir=None):
    """
    Check if auto-backup is due and create one if needed.
    
    Uses the Synesius pattern: all change-detection state lives in an
    external JSON file, never in the database itself. Change detection
    uses SHA-256 hash comparison of the database file.
    
    This should be called AFTER db.checkpoint() to ensure WAL is flushed.
    
    Frequencies:
    - 'startup': backup every session (if data changed)
    - 'daily': backup once per calendar day (if data changed)
    - 'weekly': backup once per calendar week (if data changed)
    - 'manual': never auto-backup
    
    Returns:
        dict with backup info, None if no backup needed, or raises exception
    """
    frequency = db.get_setting('backup_frequency', 'daily')
    if frequency == 'manual':
        return None
    
    state = _read_backup_state()
    
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
        return None
    
    # Check if data actually changed (hash comparison)
    current_hash = _get_db_hash()
    if current_hash is None:
        return None
    
    last_hash = state.get('last_backup_hash')
    
    if current_hash == last_hash:
        # No changes - just record that we checked
        state['last_backup_check'] = datetime.now().isoformat()
        _write_backup_state(state)
        return None
    
    # Data changed and backup is due - create backup
    if backup_dir is None:
        backup_dir = get_backup_dir(db)
    
    result = create_backup(backup_dir, db)
    
    if result:
        db.set_setting('last_auto_backup', datetime.now().isoformat())
        
        # Cleanup old backups
        retention = db.get_setting('backup_retention', '6_months')
        if retention != 'forever':
            custom_loc = db.get_setting('backup_location', '')
            cleanup_old_backups(retention, custom_loc if custom_loc else None)
        
        # Checkpoint to flush set_setting writes, then hash
        # so stored hash matches what we'll see next time
        db.checkpoint()
        final_hash = _get_db_hash()
        _write_backup_state({
            'last_backup_hash': final_hash,
            'last_backup_check': datetime.now().isoformat()
        })
    
    return result


# Legacy functions for compatibility (can be removed later)
def check_backup_needed(frequency='daily'):
    """
    Check if an automatic backup should run.
    
    Uses CALENDAR DATE comparison:
    - 'startup': backup every session (if data changed)
    - 'daily': check if last check was on a different calendar date
    - 'weekly': check if last check was 7+ calendar days ago
    - 'manual': never auto-backup
    
    Returns:
        True if backup should run, False otherwise
    """
    if frequency == 'manual':
        return False
    
    manifest = load_manifest()
    backups = manifest['backups']
    
    if not backups:
        return True
    
    all_backups = [b for b in backups if b['type'] in ('full', 'incremental')]
    
    if not all_backups:
        return True
    
    if frequency == 'startup':
        return True
    
    now = datetime.now()
    today = now.date()
    
    last_check = manifest.get('last_backup_check')
    if last_check:
        last_date = datetime.fromisoformat(last_check).date()
    else:
        last_any = max(all_backups, key=lambda x: x['created_at'])
        last_date = datetime.fromisoformat(last_any['created_at']).date()
    
    if frequency == 'daily' and today > last_date:
        return True
    elif frequency == 'weekly' and (today - last_date).days >= 7:
        return True
    
    return False


def record_backup_check():
    """
    Record that we checked for backup today.
    Called after backup attempt (whether successful or no changes).
    """
    manifest = load_manifest()
    manifest['last_backup_check'] = datetime.now().isoformat()
    save_manifest(manifest)


def get_backup_status():
    """
    Get current backup status for display.
    
    Returns dict with status info.
    """
    manifest = load_manifest()
    backups = [b for b in manifest['backups'] if b['type'] in ('full', 'incremental')]
    
    if not backups:
        return {
            'has_backups': False,
            'last_backup': None,
            'last_backup_display': 'Never',
            'backup_count': 0
        }
    
    last = max(backups, key=lambda x: x['created_at'])
    last_datetime = datetime.fromisoformat(last['created_at'])
    last_date = last_datetime.date()
    
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    
    time_str = last_datetime.strftime('%I:%M %p').lstrip('0')
    
    if last_date == today:
        diff_seconds = (now - last_datetime).total_seconds()
        if diff_seconds < 60:
            display = "Just now"
        elif diff_seconds < 3600:
            minutes = int(diff_seconds // 60)
            display = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            display = f"Today at {time_str}"
    elif last_date == yesterday:
        display = f"Yesterday at {time_str}"
    else:
        days_ago = (today - last_date).days
        if days_ago < 7:
            display = f"{days_ago} days ago"
        else:
            display = last_datetime.strftime('%B %d, %Y')
    
    return {
        'has_backups': True,
        'last_backup': last['created_at'],
        'last_backup_display': display,
        'last_backup_type': last['type'],
        'backup_count': len(backups)
    }


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


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f} MB'


def get_backup_location_setting(db):
    """Get current backup location from database settings."""
    if db:
        return db.get_setting('backup_location', '')
    return ''


def get_backup_dir(db=None):
    """Get the current backup directory (custom or default)."""
    if db:
        custom_location = db.get_setting('backup_location', '')
        if custom_location:
            return Path(custom_location)
    return BACKUPS_DIR
