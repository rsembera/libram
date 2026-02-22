# WAL Checkpoint and Backup Hash Baseline Handling in Libram

**Document Created:** February 16, 2026  
**Related Issue:** EdgeCase WAL Checkpoint Backup Issue (December 2025)

---

## Background

SQLite's WAL (Write-Ahead Logging) mode can cause false-positive backup triggers. When a WAL checkpoint occurs, the binary content of the `.db` file changes even though the logical data hasn't. Hash-based change detection sees this as a "change" and triggers unnecessary backups.

EdgeCase and MailRepo addressed this with a `refresh_hash_baseline()` function that must be called after every `checkpoint()`. Libram takes a different architectural approach that avoids needing this manual coordination.

---

## Libram's Approach

### External State File

Libram stores backup state in `data/.backup_state.json` rather than in the database itself. This contains:

```json
{
  "last_backup_hash": "sha256...",
  "last_backup_check": "2026-02-16T15:30:00"
}
```

**Why this matters:** Any "did the database change?" check that stores its answer *in the database* will always see changes (circular modification). By using an external file, Libram avoids this trap entirely.

### Frequency-First Checking

In `check_and_run_auto_backup()`, Libram checks whether a backup is due based on frequency settings **before** comparing hashes:

```python
# Check if backup is due based on frequency FIRST
if not backup_due:
    return None  # Exit early - no hash comparison happens
```

This prevents unnecessary hash comparisons that could be affected by WAL checkpoint timing.

### Post-Backup Re-Hashing

After creating a backup (which writes to the database via `set_setting()`), Libram checkpoints and captures the **final** hash:

```python
# After backup creation:
db.checkpoint()
final_hash = _get_db_hash()
_write_backup_state({
    'last_backup_hash': final_hash,
    'last_backup_check': datetime.now().isoformat()
})
```

This ensures the stored hash reflects the post-checkpoint state, so the next comparison won't see a false positive.

---

## Code Locations

| File | Function | Purpose |
|------|----------|---------|
| `core/backup.py` | `_get_backup_state_file()` | Returns path to `.backup_state.json` |
| `core/backup.py` | `_read_backup_state()` | Reads external state file |
| `core/backup.py` | `_write_backup_state()` | Writes external state file |
| `core/backup.py` | `check_and_run_auto_backup()` | Main auto-backup logic with frequency-first check |
| `web/blueprints/auth.py` | `logout()` | Calls checkpoint then auto-backup check |
| `main.py` | `_cleanup()`, `shutdown_handler()` | Shutdown backup and checkpoint |

---

## Comparison with EdgeCase/MailRepo Pattern

| Aspect | EdgeCase/MailRepo | Libram |
|--------|-------------------|--------|
| State storage | In database (manifest) | External JSON file |
| Hash baseline refresh | Manual `refresh_hash_baseline()` after checkpoint | Automatic via external state |
| Checkpoint coordination | Must call refresh after every checkpoint | No manual coordination needed |
| Complexity | Requires discipline at every checkpoint site | Self-contained in backup module |

---

## Shutdown Flow

The shutdown handlers in `main.py` call:

1. `check_auto_backup(app)` - runs backup if due
2. `db.checkpoint()` - flushes WAL to main database

The checkpoint happens **after** the backup check, but since the hash baseline is stored externally, this doesn't cause issues. The next session's backup check will see the same hash (assuming no data changes).

---

## Key Takeaways

1. **External state avoids circular modification** - The fundamental insight that checking database state shouldn't modify the database

2. **No manual coordination required** - Unlike the `refresh_hash_baseline()` pattern, developers don't need to remember to call anything after checkpoints

3. **Frequency-first prevents unnecessary work** - By checking timing before hashing, we avoid the WAL timing issue in most cases

4. **Post-backup re-hash captures final state** - When a backup does run, we ensure the stored hash reflects all changes including the backup's own database writes

---

## Testing

To verify the system is working correctly:

1. Start Libram and make a change
2. Log out (triggers backup check)
3. Log back in and immediately log out again
4. Check `data/.backup_state.json` - hash should be unchanged
5. Check `backups/` - no new backup should be created

If unnecessary backups are appearing, check:
- Is `.backup_state.json` being written correctly?
- Is the hash being captured **after** the post-backup checkpoint?
- Are there any code paths that checkpoint without going through `check_and_run_auto_backup()`?

---

*Reference document for Libram backup system architecture*
