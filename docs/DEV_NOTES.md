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

**Loading (Nov 2026):** The main page used to request every thumbnail at once, including those in collapsed years and in the hidden compact layout while in detailed view. With 4 Waitress threads that queued requests on every page load ("Task queue depth" warnings, ~1,800 in six weeks). Three changes: thumbnails are `loading="lazy"` (only visible ones are fetched), covers and thumbnails are sent with `Cache-Control: private, max-age=31536000, immutable` (filenames are unique per upload, so they never go stale), and Waitress runs 8 threads (`LIBRAM_THREADS`), more than the 6 connections a browser opens per site.

**Gotcha — session cookie vs. browser cache:** `Cache-Control` alone did nothing at first. Every authenticated response carries a refreshed session cookie and `Vary: Cookie`, so the cached image never matched the next request and the browser re-validated all of them. Cover responses now set `g.skip_session_cookie`, which `LibramSessionInterface` (in `app.py`) honours by leaving the cookie and `Vary` header off. The login check still runs on the request.

---

## WAL Mode and Backup Integrity

SQLite WAL (Write-Ahead Logging) is enabled in `connect()`. This means recent writes may be in the WAL file rather than the main `.db` file. Copying just the `.db` file without checkpointing can produce an incomplete backup.

**Fix, part 1:** `db.checkpoint()` (which runs `PRAGMA wal_checkpoint(TRUNCATE)`) is called before every backup.

**Fix, part 2 (Nov 2026):** A checkpoint is silently skipped while another connection is reading (the session-status poller runs on its own Waitress thread), so the checkpoint alone is not a guarantee. Backups now zip a snapshot taken with SQLite's backup API (`_consistent_sources()` in `core/backup.py`), which includes WAL content and can't catch the file mid-write. Hashes in the manifest are taken from that snapshot, so "what was hashed" and "what was zipped" are always the same bytes.

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

**Hash recording:** After backup, checkpoint the DB, THEN hash and store, so the stored hash matches what we'll see next time. Nothing is written to the database after a backup (the old `last_auto_backup` setting was never read and made every backed-up database look changed again).

---

## Restore: Order of Operations in a Chain

**Bug (fixed Nov 2026, same one found in Hermanubis):** restore collected the deletion lists from every incremental and applied them all at the end. A file deleted in one incremental and back in a later one was extracted and then deleted again. Reachable from the UI: delete a book with a cover → back up → restore to before the delete → back up → restore the newest point.

**Rule:** apply archives oldest first, and for each incremental apply its deletion list *before* extracting its files. The list names files that were gone when that incremental was made; the files inside it existed at that moment. See `_stage_backup_chain()`.

**Related rules:**
- A chain stops at its first missing zip. Later incrementals depend on the missing one, so they are not offered as restore points.
- Covers are always replaced, even when the backup has none; otherwise covers newer than the backup linger.
- The database and secret key are swapped in with copy-to-temp + `os.replace`, never unlink-then-copy.
- `manifest.json` is written atomically and mirrored into any custom backup folder. `recover_manifest()` adopts that mirror, or rebuilds the chains from the zip filenames, when the local manifest is missing. After a recovery the next backup is always a full one.

**Tests:** `test_backup_restore.py` (runs entirely in temp folders).

---

## Day Counts and Daylight Saving Time

Dates are stored as local-midnight Unix timestamps. A span that crosses the spring clock change is an hour short of a whole number of days, so `(finished - begun) // 86400 + 1` came out one day low (March 1–20 showed 19 days). Use `round((finished - begun) / 86400) + 1` in Python and `ROUND(.../86400.0) + 1` in SQL. Never floor.

---

## Session Keep-Alive

The session-status poll deliberately does not count as activity. Typing and clicking do: `base.html` notes them and POSTs `/api/keep-alive` at most once a minute, so writing long notes on the book form no longer runs out the session. "Stay Logged In" uses the same endpoint instead of reloading the page (a reload discards unsaved edits and trips the form guard's leave prompt).

Desktop mode: the login and setup pages ping `/api/session-status` so the heartbeat monitor sees them, the timeout is 90 seconds (browsers throttle background-tab timers to once a minute), and the monitor resets the clock after the computer wakes from sleep.

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

Rating colors validated as hex format. Card order validated against known card IDs. Background style must be empty or `user:<an uploaded file that exists>`; book type colors must be `#RRGGBB` (both end up inside inline `style` attributes).

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
| `LIBRAM_THREADS` | `8` | Waitress worker threads |
