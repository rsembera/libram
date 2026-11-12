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
- user_backgrounds/ (uploaded background images)
"""

from __future__ import annotations

import contextlib
import os
import re
import json
import hashlib
import sqlite3
import tempfile
import zipfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# App root is parent of 'core' directory
APP_ROOT = Path(__file__).parent.parent
DATA_DIR = APP_ROOT / 'data'
COVERS_DIR = APP_ROOT / 'covers'
BACKUPS_DIR = APP_ROOT / 'backups'
MANIFEST_FILE = BACKUPS_DIR / 'manifest.json'
USER_BG_DIR = APP_ROOT / 'web' / 'static' / 'user_backgrounds'

# Name of the database inside every backup zip. Fixed, regardless of where
# the live database file actually lives (see _db_path).
DB_ARCNAME = 'data/libram.db'
METADATA_NAME = '_backup_metadata.json'

# libram_<kind>_<YYYY-MM-DD_HHMMSS>[_n].zip
_BACKUP_NAME_RE = re.compile(
    r'^libram_(full|incr|pre_restore)_(\d{4}-\d{2}-\d{2}_\d{6})(?:_\d+)?\.zip$'
)


def _db_path() -> Path:
    """Path of the live database. Honours LIBRAM_DB_PATH, like the web app."""
    override = os.environ.get('LIBRAM_DB_PATH')
    return Path(override) if override else DATA_DIR / 'libram.db'


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
    db_path = _db_path()
    if db_path.exists():
        files[DB_ARCNAME] = db_path
    
    # Secret key (essential for session security)
    secret_key_path = DATA_DIR / '.secret_key'
    if secret_key_path.exists():
        files['data/.secret_key'] = secret_key_path
    
    # Cover images
    if COVERS_DIR.exists():
        for filepath in COVERS_DIR.rglob('*'):
            if filepath.is_file() and not filepath.name.startswith('.'):
                rel_path = filepath.relative_to(COVERS_DIR)
                files[f'covers/{rel_path.as_posix()}'] = filepath
    
    # Uploaded background images (referenced by the background_style setting)
    if USER_BG_DIR.exists():
        for filepath in USER_BG_DIR.iterdir():
            if filepath.is_file() and not filepath.name.startswith('.'):
                files[f'user_backgrounds/{filepath.name}'] = filepath
    
    return files


@contextlib.contextmanager
def _consistent_sources(files):
    """
    Yield {relative_path: path_to_read} for a backup, with the live database
    swapped for a consistent snapshot taken through SQLite's backup API.

    Zipping the live .db file directly can miss commits still sitting in the
    WAL (a checkpoint is skipped, without error, while another connection is
    reading) or catch the file mid-write. The snapshot has neither problem.
    """
    live_db = files.get(DB_ARCNAME)
    if live_db is None:
        yield files
        return
    
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / 'libram.db'
        try:
            src = sqlite3.connect(str(live_db))
            try:
                dst = sqlite3.connect(str(snapshot))
                try:
                    src.backup(dst)
                finally:
                    dst.close()
            finally:
                src.close()
        except sqlite3.Error:
            # Not readable as SQLite: fall back to copying the file as-is
            snapshot = live_db
        
        sources = dict(files)
        sources[DB_ARCNAME] = snapshot
        yield sources


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



def _empty_manifest():
    return {
        'backups': [],
        'last_full_hashes': {},
        'current_chain_id': None,
        'last_backup_check': None
    }


def _write_json_atomic(path, data, **dump_kwargs):
    """Write JSON via a temp file + rename so a crash can't leave half a file."""
    path = Path(path)
    tmp_path = path.with_name(path.name + '.tmp')
    with open(tmp_path, 'w') as f:
        json.dump(data, f, **dump_kwargs)
    os.replace(tmp_path, path)


def load_manifest():
    """Load backup manifest from disk."""
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, 'r') as f:
                manifest = json.load(f)
            if not isinstance(manifest, dict) or not isinstance(manifest.get('backups'), list):
                raise ValueError('unexpected manifest structure')
            for key, default in _empty_manifest().items():
                manifest.setdefault(key, default)
            return manifest
        except (json.JSONDecodeError, ValueError, OSError):
            # Manifest corrupted - backup the bad file and start fresh
            try:
                shutil.copy(MANIFEST_FILE, MANIFEST_FILE.with_suffix('.json.corrupted'))
            except OSError:
                pass
    return _empty_manifest()


def save_manifest(manifest):
    """
    Save backup manifest to disk.

    Also mirrors it into every other folder that holds backups (e.g. a cloud
    folder), so the backups there can still be restored if this machine's
    copy of the manifest is lost. See recover_manifest().
    """
    ensure_backup_dir()
    _write_json_atomic(MANIFEST_FILE, manifest, indent=2)
    
    mirror_dirs = {b.get('backup_dir') for b in manifest.get('backups', [])}
    for mirror_dir in mirror_dirs:
        if not mirror_dir:
            continue
        mirror = Path(mirror_dir) / 'manifest.json'
        if mirror == MANIFEST_FILE:
            continue
        try:
            if mirror.parent.is_dir():
                _write_json_atomic(mirror, manifest, indent=2)
        except OSError:
            pass  # Mirror is best-effort


def recover_manifest(search_dirs=()):
    """
    Rebuild the manifest when it is missing or empty but backup zips exist.

    Looks in the default backups folder plus any `search_dirs` (the custom
    backup location). Prefers a mirrored manifest.json found there; otherwise
    reconstructs the chains from the zip filenames (each full backup starts a
    chain, and the incrementals that follow it belong to that chain).

    Does nothing if the manifest already lists backups.
    Returns the number of backups recovered.
    """
    manifest = load_manifest()
    if manifest['backups']:
        return 0
    
    dirs = []
    for d in [BACKUPS_DIR, *search_dirs]:
        if not d:
            continue
        d = Path(d)
        if d.is_dir() and d not in dirs:
            dirs.append(d)
    
    # 1. A mirrored manifest written by save_manifest()
    for d in dirs:
        mirror = d / 'manifest.json'
        if mirror == MANIFEST_FILE or not mirror.exists():
            continue
        try:
            with open(mirror, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError, OSError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get('backups'), list) or not data['backups']:
            continue
        # Point each entry at wherever its zip actually is on this machine
        for entry in data['backups']:
            recorded = Path(entry.get('backup_dir') or BACKUPS_DIR) / entry['filename']
            if not recorded.exists():
                for candidate in dirs:
                    if (candidate / entry['filename']).exists():
                        entry['backup_dir'] = str(candidate)
                        break
        for key, default in _empty_manifest().items():
            data.setdefault(key, default)
        data['last_full_hashes'] = {}  # Unknown local state: next backup is a full one
        save_manifest(data)
        return len(data['backups'])
    
    # 2. No manifest anywhere: reconstruct from the zip files themselves
    found = []
    for d in dirs:
        for zip_path in d.glob('libram_*.zip'):
            match = _BACKUP_NAME_RE.match(zip_path.name)
            if not match:
                continue
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    file_count = len([n for n in zf.namelist() if n != METADATA_NAME])
            except (zipfile.BadZipFile, OSError):
                continue
            created = datetime.strptime(match.group(2), '%Y-%m-%d_%H%M%S')
            found.append((created, zip_path.name, match.group(1), zip_path, file_count))
    found.sort(key=lambda item: (item[0], item[1]))
    
    chain_id = None
    for position, (created, _name, kind, zip_path, file_count) in enumerate(found):
        # Filenames only have one-second resolution; keep same-second
        # backups in order by nudging each timestamp by its position
        created = created + timedelta(microseconds=position)
        if kind == 'full':
            chain_id = created.strftime('%Y%m%d_%H%M%S')
            backup_type, entry_chain = 'full', chain_id
        elif kind == 'pre_restore':
            backup_type, entry_chain = 'pre_restore', 'pre_restore'
        elif chain_id is None:
            continue  # Incremental with no full backup before it: unusable
        else:
            backup_type, entry_chain = 'incremental', chain_id
        manifest['backups'].append({
            'filename': zip_path.name,
            'type': backup_type,
            'chain_id': entry_chain,
            'created_at': created.isoformat(),
            'file_count': file_count,
            'backup_size': zip_path.stat().st_size,
            'backup_dir': str(zip_path.parent)
        })
    
    if manifest['backups']:
        manifest['current_chain_id'] = chain_id
        manifest['last_full_hashes'] = {}
        save_manifest(manifest)
    return len(manifest['backups'])


def generate_backup_filename(backup_type, backup_dir=None):
    """Generate unique backup filename (never one that already exists in backup_dir)."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"libram_{backup_type}_{timestamp}.zip"
    if backup_dir is not None:
        counter = 2
        while (Path(backup_dir) / filename).exists():
            filename = f"libram_{backup_type}_{timestamp}_{counter}.zip"
            counter += 1
    return filename


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
                return False, "Cloud folder not accessible. Please check your internet connection."
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
    
    files = get_all_backup_files()
    if not files:
        raise ValueError("No files to backup")
    
    filename = generate_backup_filename('full', backup_dir)
    backup_path = backup_dir / filename
    
    # Calculate hashes and create zip
    hashes = {}
    total_size = 0
    
    try:
        with _consistent_sources(files) as sources:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for rel_path, src_path in sources.items():
                    zf.write(src_path, rel_path)
                    hashes[rel_path] = get_file_hash(src_path)
                    total_size += src_path.stat().st_size
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
    
    # Note: despite the name, last_full_hashes is the state as of the most
    # recent backup in the chain (full or incremental).
    previous_hashes = manifest['last_full_hashes']
    files = get_all_backup_files()
    
    with _consistent_sources(files) as sources:
        # Hash exactly what would be written, so hashes and contents agree
        current_hashes = {rel: get_file_hash(src) for rel, src in sources.items()}
        
        changed_files = {
            rel: src for rel, src in sources.items()
            if previous_hashes.get(rel) != current_hashes[rel]
        }
        deleted_files = [p for p in previous_hashes if p not in current_hashes]
        
        if not changed_files and not deleted_files:
            return None  # No changes
        
        filename = generate_backup_filename('incr', backup_dir)
        backup_path = backup_dir / filename
        total_size = 0
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for rel_path, src_path in changed_files.items():
                    zf.write(src_path, rel_path)
                    total_size += src_path.stat().st_size
                
                # Include metadata about deleted files
                if deleted_files:
                    metadata = {'deleted_files': deleted_files}
                    zf.writestr(METADATA_NAME, json.dumps(metadata))
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



def _format_restore_time(created_at):
    created = datetime.fromisoformat(created_at)
    return created.strftime('%b %d, %Y at %I:%M %p').replace(' 0', ' ')


def get_restore_points():
    """
    Get available restore points.
    
    ALL backups are valid restore points:
    - Full backups restore directly
    - Incremental backups restore by applying chain (full + incrementals)
    - Pre-restore backups are also valid restore points
    
    An incremental is only offered if the full backup and every incremental
    before it are still on disk; a chain with a missing link stops there.
    
    Returns list of restore points with display info.
    """
    manifest = load_manifest()
    
    def path_of(backup):
        return Path(backup.get('backup_dir') or BACKUPS_DIR) / backup['filename']
    
    # Group by chain
    chains = {}
    restore_points = []
    for backup in manifest['backups']:
        if backup['type'] == 'pre_restore':
            # Safety backups are standalone restore points
            backup_path = path_of(backup)
            if backup_path.exists():
                restore_points.append({
                    'id': f"pre_restore_{backup['filename']}",
                    'filename': backup['filename'],
                    'display_name': f"{_format_restore_time(backup['created_at'])} (Safety backup)",
                    'created_at': backup['created_at'],
                    'type': 'pre_restore',
                    'is_safety': True,
                    'chain_id': 'pre_restore',
                    'dependent_count': 0,
                    'files_needed': [str(backup_path)]
                })
            continue
        
        chain = chains.setdefault(backup['chain_id'], {'full': None, 'incrementals': []})
        if backup['type'] == 'full':
            chain['full'] = backup
        else:
            chain['incrementals'].append(backup)
    
    for chain_id, chain in chains.items():
        full_backup = chain['full']
        if not full_backup:
            continue  # Skip orphaned incrementals
        
        full_path = path_of(full_backup)
        if not full_path.exists():
            continue  # Nothing in this chain can be restored without its full backup
        
        # Sort incrementals by date
        chain['incrementals'].sort(key=lambda x: x['created_at'])
        
        restore_points.append({
            'id': f"{chain_id}_full",
            'filename': full_backup['filename'],
            'display_name': _format_restore_time(full_backup['created_at']),
            'created_at': full_backup['created_at'],
            'type': 'full',
            'is_safety': False,
            'chain_id': chain_id,
            'dependent_count': len(chain['incrementals']),
            'files_needed': [str(full_path)]
        })
        
        # Each incremental is also a restore point, as long as the chain
        # leading up to it is unbroken
        files_needed = [str(full_path)]
        for i, incr in enumerate(chain['incrementals']):
            incr_path = path_of(incr)
            if not incr_path.exists():
                break  # Later incrementals depend on this one
            files_needed = files_needed + [str(incr_path)]
            
            restore_points.append({
                'id': f"{chain_id}_incr_{i}",
                'filename': incr['filename'],
                'display_name': _format_restore_time(incr['created_at']),
                'created_at': incr['created_at'],
                'type': 'incremental',
                'is_safety': False,
                'chain_id': chain_id,
                'dependent_count': 0,
                'files_needed': files_needed.copy()
            })
    
    restore_points.sort(key=lambda x: x['created_at'], reverse=True)
    return restore_points


def create_pre_restore_backup():
    """Create a backup of current state before restore (safety net)."""
    ensure_backup_dir()
    
    files = get_all_backup_files()
    if not files:
        return None
    
    filename = generate_backup_filename('pre_restore', BACKUPS_DIR)
    backup_path = BACKUPS_DIR / filename
    
    with _consistent_sources(files) as sources:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for rel_path, src_path in sources.items():
                zf.write(src_path, rel_path)
    
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


def _stage_backup_chain(backup_paths, staging_path):
    """
    Rebuild the state captured by a restore point inside `staging_path`.

    Archives are applied oldest first. An incremental's deletion list is
    applied BEFORE its own files are extracted: the list names files that
    were gone when that incremental was made, while the files inside it are
    ones that existed at that moment. Doing it in this order means a file
    deleted in one incremental and added back in a later one survives.
    """
    staging_root = staging_path.resolve()
    
    for backup_path in backup_paths:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            names = zf.namelist()
            
            if METADATA_NAME in names:
                metadata = json.loads(zf.read(METADATA_NAME))
                for rel_path in metadata.get('deleted_files', []):
                    staged_file = (staging_path / rel_path).resolve()
                    if staged_file.is_relative_to(staging_root) and staged_file.is_file():
                        staged_file.unlink()
            
            for name in names:
                if name != METADATA_NAME:
                    zf.extract(name, staging_path)


def _replace_file(staged_file, target):
    """Replace `target` with `staged_file` without ever leaving it missing."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_target = target.with_name(target.name + '.restoring')
    shutil.copy2(staged_file, tmp_target)
    os.replace(tmp_target, target)


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
        ValueError: If restore point not found, or one of its files is missing
    """
    restore_points = get_restore_points()
    point = next((p for p in restore_points if p['id'] == restore_point_id), None)
    
    if not point:
        raise ValueError(f"Restore point not found: {restore_point_id}")
    
    missing = [Path(p).name for p in point['files_needed'] if not Path(p).exists()]
    if missing:
        raise ValueError(f"Backup file missing: {', '.join(missing)}")
    
    # Create pre-restore backup first (safety net)
    create_pre_restore_backup()
    
    # Use a temporary staging directory
    with tempfile.TemporaryDirectory() as staging_dir:
        staging_path = Path(staging_dir)
        
        # Rebuild the backed-up state (full first, then incrementals)
        _stage_backup_chain(point['files_needed'], staging_path)
        
        # Now apply the restore
        # Replace database
        staged_db = staging_path / DB_ARCNAME
        if staged_db.exists():
            target_db = _db_path()
            # Remove stale WAL/SHM sidecar files. A concurrent connection
            # (e.g. the session-status poller in another Waitress thread)
            # can leave these behind, and SQLite pairing a stale WAL with
            # the freshly restored db file is undefined behavior.
            for suffix in ('-wal', '-shm'):
                sidecar = Path(str(target_db) + suffix)
                if sidecar.exists():
                    sidecar.unlink()
            _replace_file(staged_db, target_db)
        
        # Replace secret key if present
        staged_key = staging_path / 'data' / '.secret_key'
        if staged_key.exists():
            _replace_file(staged_key, DATA_DIR / '.secret_key')
        
        # Replace covers. Always start from an empty folder, even when the
        # backup holds no covers, so nothing newer than the backup lingers.
        staged_covers = staging_path / 'covers'
        if COVERS_DIR.exists():
            shutil.rmtree(COVERS_DIR)
        if staged_covers.exists():
            shutil.copytree(staged_covers, COVERS_DIR)
        else:
            COVERS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Replace uploaded backgrounds, if this backup includes them
        # (backups made before they were added leave the folder untouched)
        staged_backgrounds = staging_path / 'user_backgrounds'
        if staged_backgrounds.exists():
            if USER_BG_DIR.exists():
                shutil.rmtree(USER_BG_DIR)
            shutil.copytree(staged_backgrounds, USER_BG_DIR)
    
    return {
        'restored_at': datetime.now().isoformat(),
        'restored_from': point['display_name'],
        'restore_point_id': restore_point_id
    }


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
    - Safety (pre-restore) backups older than the retention period are deleted
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
    
    chains_to_delete = []
    manifest_changed = False
    
    # The newest chain is always kept, whatever its age
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
        manifest_changed = True
    
    # Clean up old safety backups
    for backup in safety_backups:
        if backup['created_at'] < cutoff_date:
            backup_path = Path(backup.get('backup_dir', backup_dir)) / backup['filename']
            if backup_path.exists():
                backup_path.unlink()
            if backup in manifest['backups']:
                manifest['backups'].remove(backup)
                manifest_changed = True
    
    if manifest_changed:
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
    _write_json_atomic(state_file, state)


def _get_db_hash():
    """Calculate SHA-256 hash of the database file."""
    db_path = _db_path()
    if not db_path.exists():
        return None
    return get_file_hash(db_path)


def record_backup_state(db=None):
    """
    Record the current database hash and check time in the backup state file.
    
    Called after any successful backup (manual or automatic) so that
    subsequent auto-backup checks see the current state as "already
    backed up" and don't run redundant no-op backups.
    
    Checkpoints first (if db provided) so the hash reflects all WAL content.
    """
    if db:
        db.checkpoint()
    current_hash = _get_db_hash()
    _write_backup_state({
        'last_backup_hash': current_hash,
        'last_backup_check': datetime.now().isoformat()
    })


def check_and_run_auto_backup(db, backup_dir=None):
    """
    Check if auto-backup is due and create one if needed.
    Called from logout route after WAL checkpoint.
    
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
    
    # Check if backup is due based on frequency FIRST
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
    
    # Backup is due - now check if data actually changed (hash comparison)
    current_hash = _get_db_hash()
    if current_hash is None:
        return None
    
    last_hash = state.get('last_backup_hash')
    
    if current_hash == last_hash:
        # No changes - just record that we checked
        _write_backup_state({
            'last_backup_hash': last_hash,
            'last_backup_check': datetime.now().isoformat()
        })
        return None
    
    # Data changed and backup is due - create backup
    if backup_dir is None:
        backup_dir = get_backup_dir(db)
    
    result = create_backup(backup_dir, db)
    
    if result:
        # Cleanup old backups
        retention = db.get_setting('backup_retention', '6_months')
        if retention != 'forever':
            custom_loc = db.get_setting('backup_location', '')
            cleanup_old_backups(retention, custom_loc if custom_loc else None)
        
        # Checkpoint, then hash, so the stored hash matches what the next
        # check will see. (Nothing is written to the database here: a write
        # after the backup would make the data look changed again.)
        record_backup_state(db)
    else:
        # create_backup found no file-level changes (e.g. a manual backup
        # already captured this state). Record the current hash so we
        # don't repeat this no-op check on every subsequent logout.
        _write_backup_state({
            'last_backup_hash': current_hash,
            'last_backup_check': datetime.now().isoformat()
        })
    
    return result


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
