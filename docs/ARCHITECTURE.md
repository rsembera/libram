# Libram Architecture

Technical reference for navigating and maintaining the Libram codebase.

---

## Application Structure

Libram follows the Flask application factory pattern with blueprints for route organization and a separate `core/` package for business logic.

```
libram/
├── main.py                  # Entry point (Waitress server, CLI args)
├── core/                    # Business logic (no Flask dependency except database.py's g)
│   ├── database.py          # All SQLite operations, schema, migrations
│   ├── backup.py            # Backup/restore logic, hash-based change detection
│   ├── fortunes.py          # Lazy-loads fortunes.json on first call
│   ├── fortunes.json        # 1,666 fortune strings
│   ├── astrology.py         # Sun/moon sign calculation via ephem
│   └── thumbnails.py        # Cover thumbnail generation (Pillow)
├── web/
│   ├── app.py               # Flask app factory, config, context processors
│   ├── blueprints/          # Route handlers (7 blueprints)
│   ├── static/              # CSS, JS, fonts, images
│   └── templates/           # Jinja2 templates (11 files)
├── data/                    # Runtime data (gitignored)
│   ├── libram.db            # SQLite database (WAL mode)
│   └── .secret_key          # Auto-generated Flask secret key
├── covers/                  # Cover images (gitignored)
│   └── thumbs/              # Auto-generated JPEG thumbnails
└── backups/                 # Database backups (gitignored)
```

---

## Request Flow

```
Browser → Waitress → Flask
  → before_request (session timeout check, heartbeat)
  → Blueprint route handler
  → core/database.py (SQLite operations)
  → Jinja2 template → Response
  → teardown_appcontext (close DB connection)
```

---

## Blueprints & Routes

### auth (`/login`, `/logout`, `/setup`, `/change-password`)
Authentication and session management. Login sets `session['logged_in']` and `session['last_activity']`. The `before_request` handler in `app.py` enforces timeout.

### books (`/`, `/book/new`, `/book/<id>`)
Main view and book CRUD. The index route handles search, view mode, and assembles year groups. Also serves three chart API endpoints (`/api/books-per-month`, `/api/pages-per-day-by-month`, `/api/books-by-type`).

### covers (`/covers/`)
Cover image management. Routes: `serve_cover` (full-size), `serve_thumb` (thumbnail with fallback), `upload`, `search` (Open Library ISBN lookup), `delete`. Thumbnails generated on upload/search via `core/thumbnails.py`.

### settings (`/settings/`)
Theme, font, background, rating colors, astrology toggle, border style, card order, session timeout. Each setting has its own POST API endpoint with input validation against allowlists.

### types (`/types`)
Book type CRUD. Types have name (9 char max), color, and bubble_color. Deletion blocked if books are assigned to the type.

### exports (`/export/`)
CSV and Markdown export with date range filtering and sort order. Markdown supports compact (list) and detailed (table) styles.

### backups (`/backups/`)
Backup/restore with auto-backup on logout/shutdown. Supports cloud folder detection (iCloud, Dropbox, Google Drive, OneDrive). Calendar-based scheduling: Every Session, Daily, Weekly, or Manual. WAL checkpoint before every backup copy.

---

## Database

### Connection Management
- `app.get_db()` stores connection in Flask's `g` object (per-request lifecycle)
- `teardown_appcontext` closes connection after each request
- WAL mode enabled on connect for concurrent access
- Foreign keys enabled via PRAGMA

### Schema
Three tables: `books`, `book_types`, `settings`. All timestamps stored as Unix integers. Schema created in `database.py` `_init_db()` with `CREATE TABLE IF NOT EXISTS`.

### Password Storage
Format: `pbkdf2:600000:<salt_hex>:<hash_hex>`
- 600,000 PBKDF2-HMAC-SHA256 iterations
- 16-byte random salt per password
- Legacy SHA-256 hashes (64-char hex) auto-migrate on successful login

---

## Theming System

Six themes defined in `themes.css` using CSS custom properties on `[data-theme]` selectors:

| Theme | Type | Description |
|-------|------|-------------|
| Ink | Light | Default, clean dark text on light background |
| Slate | Light | Cool gray tones |
| Parchment | Light | Warm ivory/cream |
| Witching Hour | Dark | Blue/purple, gothic |
| Crimson Veil | Dark | Black with blood red |
| Terminal | Dark | Green on black, CRT monochrome |

The context processor in `app.py` injects theme settings into every template. Theme selection stored in `settings` table.

---

## Cover Thumbnail System

`core/thumbnails.py` generates 300px-height JPEG thumbnails using Pillow:

- **On upload/ISBN fetch**: thumbnail generated immediately
- **On startup**: `generate_missing_thumbnails()` catches any covers without thumbs
- **Graceful degradation**: if Pillow unavailable, `/covers/thumb/<file>` falls back to original
- **Cleanup**: `delete_thumbnail()` called whenever a cover is removed

Compact view `<img>` tags use `/covers/thumb/` route; lightbox onclick uses `/covers/` (full-size).

---

## Session & Security

### Session Fixes (Safari/Firefox)
Four changes prevent the double-login race condition:
1. `session.clear()` before setting new values
2. `session['last_activity']` set during login (not just in `before_request`)
3. `SESSION_COOKIE_NAME = 'libram_session'`
4. `make_response()` for explicit cookie handling

### Secret Key
Auto-generated on first run via `secrets.token_hex(32)`, persisted to `data/.secret_key` with 0o600 permissions. Environment variable `LIBRAM_SECRET_KEY` takes priority if set.

### Input Validation
Settings API endpoints validate against allowlists (`VALID_THEMES`, `VALID_FONTS`, etc.) defined at module level in `settings.py`.

---

## Auto-Backup System

Triggered on logout and app shutdown (not login):

1. Check frequency setting (startup/daily/weekly/manual)
2. Compare `db_mtime` against `last_auto_backup` — skip if unchanged
3. For daily/weekly, compare calendar dates (not hours elapsed)
4. Checkpoint WAL, copy database file
5. Run retention cleanup (1 month / 6 months / 1 year / forever)

Cloud detection scans for iCloud, Dropbox, Google Drive, and OneDrive folders.

---

## Key Patterns

### Fortunes (Lazy Loading)
`core/fortunes.py` loads `fortunes.json` on first call to `get_fortune()`, caches in module-level `_fortunes`. Avoids 157KB of Python source parsing at import time.

### CSS Custom Properties
All theming via `var(--property-name)`. Theme CSS sets properties on `[data-theme]`, components reference them. No theme-specific class names in templates.

### Settings Storage
All settings in a single `settings` table (key/value). `get_setting(key, default)` and `set_setting(key, value)` are the only access pattern. No ORM.
