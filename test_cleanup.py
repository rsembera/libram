#!/usr/bin/env python3
"""
Test script for backup retention cleanup logic.
Creates mock backups with old dates and verifies cleanup works correctly.
"""

import sys
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.backup import cleanup_old_backups, save_manifest, load_manifest, MANIFEST_FILE


def create_mock_backup(backup_dir: Path, filename: str) -> Path:
    """Create a mock backup zip file."""
    import zipfile
    backup_path = backup_dir / filename
    with zipfile.ZipFile(backup_path, 'w') as zf:
        zf.writestr('test.txt', 'mock backup content')
    return backup_path


def test_cleanup():
    """Test that cleanup_old_backups correctly prunes old chains."""
    
    # Use a temp directory for test backups
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir)
        
        # Override the manifest file location for testing
        test_manifest = backup_dir / 'manifest.json'
        
        # Create dates for testing
        now = datetime.now()
        old_date = (now - timedelta(days=45)).isoformat()  # 45 days ago
        recent_date = (now - timedelta(days=5)).isoformat()  # 5 days ago
        
        # Create mock backup files
        old_full = create_mock_backup(backup_dir, 'libram_full_old.zip')
        old_incr = create_mock_backup(backup_dir, 'libram_incr_old.zip')
        new_full = create_mock_backup(backup_dir, 'libram_full_new.zip')
        new_incr = create_mock_backup(backup_dir, 'libram_incr_new.zip')
        old_safety = create_mock_backup(backup_dir, 'libram_pre_restore_old.zip')
        
        # Create manifest with old and new chains
        manifest = {
            'backups': [
                # Old chain (should be deleted with 1_month retention)
                {
                    'filename': 'libram_full_old.zip',
                    'type': 'full',
                    'chain_id': 'old_chain',
                    'created_at': old_date,
                    'file_count': 1,
                    'backup_size': 100,
                    'backup_dir': str(backup_dir)
                },
                {
                    'filename': 'libram_incr_old.zip',
                    'type': 'incremental',
                    'chain_id': 'old_chain',
                    'created_at': old_date,
                    'file_count': 1,
                    'backup_size': 50,
                    'backup_dir': str(backup_dir)
                },
                # New chain (should be kept)
                {
                    'filename': 'libram_full_new.zip',
                    'type': 'full',
                    'chain_id': 'new_chain',
                    'created_at': recent_date,
                    'file_count': 1,
                    'backup_size': 100,
                    'backup_dir': str(backup_dir)
                },
                {
                    'filename': 'libram_incr_new.zip',
                    'type': 'incremental',
                    'chain_id': 'new_chain',
                    'created_at': recent_date,
                    'file_count': 1,
                    'backup_size': 50,
                    'backup_dir': str(backup_dir)
                },
                # Old safety backup (should be deleted)
                {
                    'filename': 'libram_pre_restore_old.zip',
                    'type': 'pre_restore',
                    'chain_id': 'pre_restore',
                    'created_at': old_date,
                    'file_count': 1,
                    'backup_size': 100,
                    'backup_dir': str(backup_dir)
                }
            ],
            'last_full_hashes': {},
            'current_chain_id': 'new_chain'
        }
        
        # Write manifest to test location
        with open(test_manifest, 'w') as f:
            json.dump(manifest, f)
        
        # Temporarily override the manifest path
        import core.backup as backup_module
        original_manifest = backup_module.MANIFEST_FILE
        backup_module.MANIFEST_FILE = test_manifest
        
        try:
            print("=== Backup Cleanup Test ===\n")
            
            # Show initial state
            print("Before cleanup:")
            print(f"  Files in backup dir: {[f.name for f in backup_dir.glob('*.zip')]}")
            print(f"  Backups in manifest: {len(manifest['backups'])}")
            
            # Run cleanup with 1 month retention
            print("\nRunning cleanup_old_backups('1_month')...")
            cleanup_old_backups('1_month', str(backup_dir))
            
            # Check results
            remaining_files = list(backup_dir.glob('*.zip'))
            updated_manifest = load_manifest()
            
            print("\nAfter cleanup:")
            print(f"  Files in backup dir: {[f.name for f in remaining_files]}")
            print(f"  Backups in manifest: {len(updated_manifest['backups'])}")
            
            # Verify expectations
            print("\n=== Verification ===")
            
            # Old chain files should be deleted
            old_files_exist = old_full.exists() or old_incr.exists()
            print(f"  Old chain deleted: {'✓ PASS' if not old_files_exist else '✗ FAIL'}")
            
            # New chain files should remain
            new_files_exist = new_full.exists() and new_incr.exists()
            print(f"  New chain preserved: {'✓ PASS' if new_files_exist else '✗ FAIL'}")
            
            # Old safety backup should be deleted
            old_safety_exists = old_safety.exists()
            print(f"  Old safety deleted: {'✓ PASS' if not old_safety_exists else '✗ FAIL'}")
            
            # Manifest should only have new chain
            manifest_correct = len(updated_manifest['backups']) == 2
            print(f"  Manifest updated: {'✓ PASS' if manifest_correct else '✗ FAIL'}")
            
            # Overall result
            all_passed = not old_files_exist and new_files_exist and not old_safety_exists and manifest_correct
            print(f"\n{'='*30}")
            print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
            print(f"{'='*30}")
            
            return all_passed
            
        finally:
            # Restore original manifest path
            backup_module.MANIFEST_FILE = original_manifest


def test_keep_last_chain():
    """Test that cleanup keeps at least one chain even if all are old."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir)
        test_manifest = backup_dir / 'manifest.json'
        
        # Create a single old chain
        old_date = (datetime.now() - timedelta(days=400)).isoformat()  # Over a year old
        old_full = create_mock_backup(backup_dir, 'libram_full_ancient.zip')
        
        manifest = {
            'backups': [
                {
                    'filename': 'libram_full_ancient.zip',
                    'type': 'full',
                    'chain_id': 'only_chain',
                    'created_at': old_date,
                    'file_count': 1,
                    'backup_size': 100,
                    'backup_dir': str(backup_dir)
                }
            ],
            'last_full_hashes': {},
            'current_chain_id': 'only_chain'
        }
        
        with open(test_manifest, 'w') as f:
            json.dump(manifest, f)
        
        import core.backup as backup_module
        original_manifest = backup_module.MANIFEST_FILE
        backup_module.MANIFEST_FILE = test_manifest
        
        try:
            print("\n=== Keep Last Chain Test ===\n")
            print("Testing: Single chain that's 400 days old with 1_month retention")
            print("Expected: Chain should be KEPT (never delete the last chain)\n")
            
            cleanup_old_backups('1_month', str(backup_dir))
            
            chain_preserved = old_full.exists()
            updated_manifest = load_manifest()
            manifest_intact = len(updated_manifest['backups']) == 1
            
            print(f"  Last chain preserved: {'✓ PASS' if chain_preserved else '✗ FAIL'}")
            print(f"  Manifest intact: {'✓ PASS' if manifest_intact else '✗ FAIL'}")
            
            all_passed = chain_preserved and manifest_intact
            print(f"\n{'='*30}")
            print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
            print(f"{'='*30}")
            
            return all_passed
            
        finally:
            backup_module.MANIFEST_FILE = original_manifest


if __name__ == '__main__':
    test1 = test_cleanup()
    test2 = test_keep_last_chain()
    
    print(f"\n{'='*40}")
    print("FINAL RESULTS")
    print(f"{'='*40}")
    print(f"  Cleanup test: {'PASS' if test1 else 'FAIL'}")
    print(f"  Keep-last-chain test: {'PASS' if test2 else 'FAIL'}")
    
    sys.exit(0 if (test1 and test2) else 1)
