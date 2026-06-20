# Development Notes

Patterns, gotchas, and lessons learned during Libram development. Reference for future maintenance and for applying these patterns to other projects.

---

## Pages Per Month — Proportional Attribution

**What it does:** The "Pages Per Month" chart distributes each book's pages across the calendar months its reading spanned, weighted by how many days fell in each month. A book read June 27 → July 12 (4 days in June, 12 in July) splits its pages 25% / 75%.

**Deliberate asymmetry with "Books Per Month":** Books Per Month counts each book once, in its *finish* month. Pages Per Month *spreads* pages across the span. This is intentional — don't "fix" it to match. A 900-page book finished in July shouldn't make July look like a 900-page month if most of it was read in June.

**Why days_paused is ignored in the split:** We only store a *count* of paused days, not *which* days. Under the only assumption the data supports (pauses spread evenly), the month proportions are unchanged — pauses scale pace (pages/day), not the page split. So the attribution uses raw calendar days from `date_begun` to `date_finished` inclusive.

**In-progress books are excluded:** A book with no `date_finished` has an unknown final page count, so there's nothing reliable to attribute yet. DNF books contribute `pages_completed` over their begun→finished window.

**Where the logic lives:** `distribute_pages_across_months(begun, finished, pages)` in `core/database.py` is a pure function (no DB, no `self`) so it's directly unit-testable — see `test_pages_per_month.py`. `get_pages_per_month()` is thin glue: build 12 month buckets, run every finished/DNF book through the helper, drop contributions outside the window.

---

## Flask Session Race Condition (Safari/Firefox Double-Login)

**Problem:** After entering correct credentials, Safari and Firefox redirect back to login with `?timeout=1`. User has to log in twice. Chrome works fine.

**Root cause:** `before_request` checks `session['last_activity']` for timeout, but `last_activity` wasn't set during login — only in `before_request` itself. Safari/Firefox are stricter about cookie timing; the redirect fires before the cookie is fully persisted.

**Fix (all four required):**
1. `session.clear()` before setting new session values
2. Set `session['last_activity'] = time.time()` during login
3. Use unique cookie name: `SESSION_COOKIE_NAME = 'libram_session'`
4. Use `make_response()` for explicit cookie handling

**See also:** `Flask_Double_Login_Fix.md` in the EdgeCase project for the full writeup.

---

## PBKDF2 Password Migration

**Problem:** Passwords were stored as unsalted SHA-256 hashes. If the database file is compromised, rainbow tables crack it instantly.

**Solution:** PBKDF2-HMAC-SHA256 with 600k iterations and 16-byte random salt. Stored as `pbkdf2:600000:<salt_hex>:<hash_hex>`.

**Migration logic in `verify_password()`:**
- If stored hash starts with `pbkdf2:` → verify with PBKDF2
- If stored hash is 64-char hex (legacy SHA-256) → verify with SHA-256, then **auto-upgrade** by calling `set_password()` on success
- Migration is transparent — happens on next login, no user action needed

**Note:** Synesius uses plain SHA-256 for its stored hash because its real security layer is SQLCipher encryption. Libram's stored hash IS the only security layer, so PBKDF2 matters more here.

---

## Secret Key Auto-Generation

**Problem:** `app.secret_key` had a hardcoded fallback (`'dev-secret-key-change-in-production'`) that was actually being used in production on Sentinel.

**Solution:** `_get_or_create_secret_key()` in `app.py`:
1. Check for `data/.secret_key` file
2. If missing, generate `secrets.token_hex(32)` (64-char hex)
3. Write to file with `chmod 0o600`
4. Environment variable `LIBRAM_SECRET_KEY` still takes priority

**Side effect:** First deploy after this change invalidates all existing sessions (one-time re-login).

---

## Cover Thumbnails

**Problem:** Users uploading high-res cover scans (4.7MB PNGs) caused slow compact view loading, especially over Tailscale.

**Solution:** `core/thumbnails.py` generates 300px-height JPEG thumbnails at save time:
- Generated on upload, ISBN fetch, and at app startup (migration for existing covers)
- Stored in `covers/thumbs/` as `<stem>_thumb.jpg`
- Compact view uses `/covers/thumb/<filename>` route (falls back to original if no thumb)
- Lightbox still loads full-size via `/covers/<filename>`
- Graceful degradation: if Pillow not installed, serves originals (no crash)

**Dependency:** `Pillow>=10.0.0` added to requirements.txt.

---

## WAL Mode and Backup Integrity

SQLite WAL (Write-Ahead Logging) is enabled in `connect()`. This means recent writes may be in the WAL file rather than the main `.db` file. Copying just the `.db` file without checkpointing can produce an incomplete backup.

**Fix:** `db.checkpoint()` (which runs `PRAGMA wal_checkpoint(TRUNCATE)`) is called before every `shutil.copy2()` in both `create_backup()` and `_create_auto_backup()`.

---

## Fortunes: Lazy Loading from JSON

**Problem:** `core/fortunes.py` was 1,684 lines — a giant Python list literal (157KB) parsed by the interpreter on every import.

**Solution (matching Synesius pattern):**
- Extract list to `core/fortunes.json`
- Module-level `_fortunes: list[str] | None = None`
- `_load_fortunes()` reads JSON on first call, caches in module global
- `get_fortune()` calls `_load_fortunes()` then `random.choice()`

---

## Auto-Backup System

**Key design decisions:**
1. Triggered on logout (not login) — avoids backing up before user makes changes
2. Calendar-based frequency: Daily = different calendar day, Weekly = 7+ days
3. Change detection via SHA-256 hash comparison (not mtime)
4. State stored in external JSON file (`data/.backup_state.json`), never in database

**Critical fix (Feb 2026):** Must check frequency FIRST, then hash. The reverse order caused backups on every logout because reading DB settings could affect timing. Pattern matches Synesius.

```python
# CORRECT order (frequency first)
if frequency == 'manual':
    return None
if not backup_due:  # Check date/frequency
    return None
if current_hash == last_hash:  # Then check hash
    return None
# Now create backup
```

**Hash recording:** After backup, checkpoint the DB (to flush `last_auto_backup` setting write), THEN hash and store. This ensures the stored hash matches what we'll see next time.

---

## Settings Input Validation

Settings API endpoints now validate against module-level allowlists:

```python
VALID_THEMES = {'ink', 'slate', 'parchment', 'witching-hour', 'crimson-veil', 'terminal'}
VALID_FONTS = {'lexend', 'libre-baskerville', 'lora', 'source-sans', 'literata'}
VALID_SIZES = {'s', 'm', 'l'}
VALID_BORDERS = {'accent', 'vibrant'}
VALID_TIMEOUTS = {'0', '15', '30', '60', '120'}
```

Rating colors validated as hex format. Card order validated against known card IDs. Background style and astrology toggle left as freeform (no security risk).

---

## Cross-Project Patterns

These patterns are shared with Synesius and/or EdgeCase:

| Pattern | Origin | Notes |
|---------|--------|-------|
| Session race condition fix | EdgeCase | All four fixes required |
| Fortunes lazy-load from JSON | Synesius | Identical module structure |
| Secret key auto-generation | Synesius | Same `_get_or_create_secret_key()` pattern |
| WAL mode + checkpoint before backup | Synesius | Standard SQLite best practice |
| CSS custom properties for theming | Synesius | Theme system inherited, expanded |
| `get_setting()` / `set_setting()` | Synesius | Single key/value table pattern |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRAM_HOST` | `127.0.0.1` | Server bind address |
| `LIBRAM_PORT` | `8090` | Server port |
| `LIBRAM_SECRET_KEY` | (auto-generated) | Flask secret key override |
| `LIBRAM_DB_PATH` | `data/libram.db` | Database file location |
| `LIBRAM_BROWSER` | unset | Set to `1` to auto-open browser on start |
| `LIBRAM_DESKTOP` | unset | Set to `1` for desktop mode (heartbeat monitoring) |
