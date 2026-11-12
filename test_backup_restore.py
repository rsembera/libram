#!/usr/bin/env python3
"""
Test script for backup chains and restore.

Runs entirely inside temporary directories (core.backup's module-level paths
are pointed at a scratch folder for each test), so it never touches real data.

    ./venv/bin/python test_backup_restore.py
"""

import os
import sys
import json
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import core.backup as backup

_PATH_ATTRS = ('APP_ROOT', 'DATA_DIR', 'COVERS_DIR', 'BACKUPS_DIR', 'MANIFEST_FILE', 'USER_BG_DIR')


@contextmanager
def sandbox():
    """Point core.backup at a fresh temp folder; restore the real paths after."""
    saved = {name: getattr(backup, name) for name in _PATH_ATTRS}
    saved_env = os.environ.pop('LIBRAM_DB_PATH', None)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        backup.APP_ROOT = root
        backup.DATA_DIR = root / 'data'
        backup.COVERS_DIR = root / 'covers'
        backup.BACKUPS_DIR = root / 'backups'
        backup.MANIFEST_FILE = backup.BACKUPS_DIR / 'manifest.json'
        backup.USER_BG_DIR = root / 'web' / 'static' / 'user_backgrounds'
        backup.DATA_DIR.mkdir()
        (backup.COVERS_DIR / 'thumbs').mkdir(parents=True)
        try:
            yield root
        finally:
            for name, value in saved.items():
                setattr(backup, name, value)
            os.environ.pop('LIBRAM_DB_PATH', None)
            if saved_env is not None:
                os.environ['LIBRAM_DB_PATH'] = saved_env


def write_db(text):
    """Stand-in database: any bytes will do for chain tests."""
    (backup.DATA_DIR / 'libram.db').write_text(text)


def read_db():
    return (backup.DATA_DIR / 'libram.db').read_text()


def newest_point():
    return [p for p in backup.get_restore_points() if not p['is_safety']][0]


def point_for(info):
    return next(p for p in backup.get_restore_points() if p['filename'] == info['filename'])


# ---------------------------------------------------------------------------

def test_delete_then_readd_survives():
    """A file deleted in one incremental and re-added in a later one must survive restore."""
    with sandbox():
        cover = backup.COVERS_DIR / 'aaaa.jpg'
        write_db('v1'); cover.write_text('cover')
        backup.create_backup()                      # full: cover present
        cover.unlink(); write_db('v2')
        incr1 = backup.create_backup()              # incr 1: records the deletion
        cover.write_text('cover again'); write_db('v3')
        backup.create_backup()                      # incr 2: cover is back
        cover.unlink(); write_db('scribble')

        backup.restore_immediate(newest_point()['id'])
        ok = cover.exists() and cover.read_text() == 'cover again' and read_db() == 'v3'

        # ...and restoring the middle point must still honour the deletion
        backup.restore_immediate(point_for(incr1)['id'])
        return ok and not cover.exists() and read_db() == 'v2'


def test_restore_then_continue_chain():
    """Delete a book, restore to before the delete, keep backing up, restore the newest point."""
    with sandbox():
        cover = backup.COVERS_DIR / 'bbbb.jpg'
        write_db('v1'); cover.write_text('cover')
        full = backup.create_backup()
        cover.unlink(); write_db('v2 book deleted')
        backup.create_backup()
        backup.restore_immediate(point_for(full)['id'])   # back to before the delete
        write_db('v3 another book added')
        backup.create_backup()
        cover.unlink(); write_db('scribble')

        backup.restore_immediate(newest_point()['id'])
        return cover.exists() and read_db() == 'v3 another book added'


def test_broken_chain_stops_at_missing_link():
    """If an incremental's zip is gone, later points in that chain must not be offered."""
    with sandbox():
        write_db('v1'); full = backup.create_backup()
        write_db('v2'); incr1 = backup.create_backup()
        write_db('v3'); incr2 = backup.create_backup()
        (backup.BACKUPS_DIR / incr1['filename']).unlink()

        offered = {p['filename'] for p in backup.get_restore_points()}
        ok = full['filename'] in offered and incr2['filename'] not in offered

        # Chain whose full backup is gone offers nothing at all
        (backup.BACKUPS_DIR / full['filename']).unlink()
        return ok and not [p for p in backup.get_restore_points() if not p['is_safety']]


def test_restore_clears_newer_covers():
    """Restoring a point that had no covers must not leave later covers behind."""
    with sandbox():
        write_db('v1'); full = backup.create_backup()
        later = backup.COVERS_DIR / 'later.jpg'
        later.write_text('x'); write_db('v2')

        backup.restore_immediate(point_for(full)['id'])
        return not later.exists() and backup.COVERS_DIR.is_dir() and read_db() == 'v1'


def test_all_safety_backups_listed():
    """Every pre-restore safety backup is its own restore point."""
    with sandbox():
        write_db('v1'); full = backup.create_backup()
        backup.restore_immediate(point_for(full)['id'])
        backup.restore_immediate(point_for(full)['id'])
        safety = [p for p in backup.get_restore_points() if p['is_safety']]
        files = {p['filename'] for p in safety}
        return len(safety) == 2 and len(files) == 2


def test_snapshot_includes_uncheckpointed_writes():
    """A backup taken while another connection holds the WAL open still gets every commit."""
    with sandbox():
        db_file = backup.DATA_DIR / 'libram.db'
        writer = sqlite3.connect(str(db_file))
        writer.execute('PRAGMA journal_mode = WAL')
        writer.execute('PRAGMA wal_autocheckpoint = 0')
        writer.execute('CREATE TABLE t (x INTEGER)')
        writer.executemany('INSERT INTO t VALUES (?)', [(i,) for i in range(50)])
        writer.commit()

        # A reader mid-transaction blocks checkpoints, so rows stay in the WAL
        reader = sqlite3.connect(str(db_file))
        reader.execute('BEGIN')
        reader.execute('SELECT COUNT(*) FROM t').fetchone()
        writer.executemany('INSERT INTO t VALUES (?)', [(i,) for i in range(50, 120)])
        writer.commit()

        full = backup.create_backup()
        unchanged = backup.create_backup()          # nothing changed: must be a no-op
        reader.close(); writer.close()

        import zipfile
        with tempfile.TemporaryDirectory() as out:
            with zipfile.ZipFile(backup.BACKUPS_DIR / full['filename']) as zf:
                zf.extract(backup.DB_ARCNAME, out)
            restored = sqlite3.connect(str(Path(out) / backup.DB_ARCNAME))
            rows = restored.execute('SELECT COUNT(*) FROM t').fetchone()[0]
            integrity = restored.execute('PRAGMA integrity_check').fetchone()[0]
            restored.close()
        return rows == 120 and integrity == 'ok' and unchanged is None


def test_manifest_recovery_by_scanning():
    """With the manifest gone, chains are rebuilt from the zip files."""
    with sandbox():
        cover = backup.COVERS_DIR / 'cccc.jpg'
        write_db('v1'); backup.create_backup()
        write_db('v2'); cover.write_text('c'); backup.create_backup()
        backup.MANIFEST_FILE.unlink()
        cover.unlink(); write_db('scribble')

        recovered = backup.recover_manifest()
        points = [p for p in backup.get_restore_points() if not p['is_safety']]
        ok = recovered == 2 and len(points) == 2 and len(points[0]['files_needed']) == 2
        backup.restore_immediate(points[0]['id'])
        ok = ok and read_db() == 'v2' and cover.exists()

        # Unknown local state after recovery, so the next backup must be a full one
        write_db('v3')
        return ok and backup.create_backup()['type'] == 'full'


def test_manifest_mirrored_to_custom_location():
    """Backups in a custom folder carry a manifest copy that can be adopted later."""
    with sandbox() as root:
        cloud = root / 'cloud' / 'Libram Backups'
        write_db('v1'); backup.create_backup(cloud)
        write_db('v2'); backup.create_backup(cloud)
        mirror = cloud / 'manifest.json'
        ok = mirror.exists() and len(json.loads(mirror.read_text())['backups']) == 2

        backup.MANIFEST_FILE.unlink()               # local manifest lost
        ok = ok and backup.recover_manifest([cloud]) == 2
        write_db('scribble')
        backup.restore_immediate(newest_point()['id'])
        return ok and read_db() == 'v2' and backup.recover_manifest([cloud]) == 0


def test_same_second_backups_do_not_collide():
    """Two backups in the same second get different filenames."""
    with sandbox():
        write_db('v1'); a = backup.create_backup()
        write_db('v2'); b = backup.create_backup()
        write_db('v3'); c = backup.create_backup()
        names = {a['filename'], b['filename'], c['filename']}
        on_disk = all((backup.BACKUPS_DIR / n).exists() for n in names)
        backup.MANIFEST_FILE.unlink()
        return len(names) == 3 and on_disk and backup.recover_manifest() == 3


def test_custom_db_path_and_backgrounds():
    """LIBRAM_DB_PATH is honoured, and uploaded backgrounds are backed up and restored."""
    with sandbox() as root:
        custom = root / 'elsewhere' / 'books.db'
        custom.parent.mkdir()
        os.environ['LIBRAM_DB_PATH'] = str(custom)
        custom.write_text('v1')
        backup.USER_BG_DIR.mkdir(parents=True)
        bg = backup.USER_BG_DIR / 'paper.png'
        bg.write_text('bg')

        full = backup.create_backup()
        custom.write_text('scribble'); bg.unlink()
        (backup.USER_BG_DIR / 'newer.png').write_text('n')
        backup.restore_immediate(point_for(full)['id'])
        return (custom.read_text() == 'v1' and bg.exists()
                and not (backup.USER_BG_DIR / 'newer.png').exists()
                and not (backup.DATA_DIR / 'libram.db').exists())


TESTS = [
    test_delete_then_readd_survives,
    test_restore_then_continue_chain,
    test_broken_chain_stops_at_missing_link,
    test_restore_clears_newer_covers,
    test_all_safety_backups_listed,
    test_snapshot_includes_uncheckpointed_writes,
    test_manifest_recovery_by_scanning,
    test_manifest_mirrored_to_custom_location,
    test_same_second_backups_do_not_collide,
    test_custom_db_path_and_backgrounds,
]


if __name__ == '__main__':
    print('=== Backup / Restore Tests ===\n')
    failed = 0
    for test in TESTS:
        try:
            passed = bool(test())
            detail = ''
        except Exception as e:  # noqa: BLE001 - report and keep going
            passed = False
            detail = f'  ({type(e).__name__}: {e})'
        failed += not passed
        print(f"  {'✓ PASS' if passed else '✗ FAIL'}  {test.__name__}{detail}")
    print(f"\n{'=' * 40}")
    print('ALL TESTS PASSED' if not failed else f'{failed} TEST(S) FAILED')
    print('=' * 40)
    sys.exit(1 if failed else 0)
