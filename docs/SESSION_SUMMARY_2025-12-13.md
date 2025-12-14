# Libram Development Session Summary
## December 13, 2025 (Saturday late night session)

### Project Overview
Libram is a personal reading tracker web application built with Flask/Python and SQLite. It's Richard's third major application following EdgeCase (client management) and Mirror (journaling). The app tracks books read with automatic calculations (days to complete, pages per day), dual numbering system (all-time and yearly), themes, and various customization options.

### Current Tech Stack
- **Backend**: Flask 3.x, SQLite (plain, no encryption)
- **Frontend**: Vanilla JS, CSS with CSS custom properties for theming
- **Icons**: Phosphor Icons
- **Fonts**: Local font files (Lexend, Outfit, Atkinson Hyperlegible, OpenDyslexic, etc.)

### Repository
- GitHub: `rsembera/libram`
- Local path: `/Users/rick/libram`
- Running on: `http://127.0.0.1:8090`
- Debug mode: **enabled** (auto-reloads on file changes)

---

## Changes Made This Session

### 1. SQLCipher Removal
Removed SQLCipher encryption in favor of plain SQLite. Rationale: encryption at rest doesn't protect against remote attackers who compromise a running server (they use the app's open DB connection). Tailscale + login password provides meaningful protection. Simplifies installation and distribution.

**Files changed:**
- `core/database.py` - Removed sqlcipher3 import, SQLCIPHER_AVAILABLE flag, password parameter, PRAGMA key

### 2. Instant Search-as-you-type
Replaced form-submit search with client-side filtering.

**Features:**
- Filters by title and author as you type
- Auto-expands year sections with matches
- Updates book counts while filtering
- X button clears and resets

**Files changed:**
- `web/templates/main_view.html` - Added `data-title` and `data-author` attributes to book cards
- `web/static/js/main_view.js` - New `filterBooks()` function, updated `initSearch()`, fixed DOMContentLoaded timing issue

### 3. UI Polish for Evening Ritual Theme
Fixed various elements that had hardcoded colors breaking dark theme:

**Settings page:**
- Auto-logout dropdown now styled to match custom dropdowns (border radius, padding, dropdown arrow)
- "Change Password" button changed to `btn-secondary` for theme-aware colors
- "Choose Image" button also changed to `btn-secondary`

**Date pickers (`pickers.css`):**
- Replaced all hardcoded colors with CSS variables
- `.picker-display`, `.picker-dropdown`, `.picker-header`, `.picker-cell`, etc.

**Backups page (`backups.css`):**
- Replaced hardcoded backgrounds with `var(--bg-secondary)`
- Text colors now use `var(--text-primary)`, `var(--text-muted)`
- Download and restore icon buttons now have `btn-secondary` class

### 4. Flask Debug Mode
Enabled `debug=True` in `main.py` for auto-reload during development.

### 5. Gitignore Update
Added `backups/` to `.gitignore` (was only ignoring `data/backups/`)

---

## Project Structure (Key Files)

```
/Users/rick/libram/
├── main.py                     # Entry point, runs Flask app
├── core/
│   └── database.py             # SQLite database class, all queries
├── web/
│   ├── app.py                  # Flask app factory
│   ├── blueprints/
│   │   ├── auth.py             # Login/logout/password
│   │   ├── books.py            # Main view, book CRUD, API endpoints
│   │   ├── settings.py         # Settings page
│   │   ├── backups.py          # Backup management
│   │   └── types.py            # Book types CRUD
│   ├── templates/
│   │   ├── base.html           # Base template with theme/font vars
│   │   ├── main_view.html      # Main book list view
│   │   ├── book_form.html      # Add/edit book form
│   │   ├── settings.html       # Settings page
│   │   ├── backups.html        # Backups page
│   │   ├── manage_types.html   # Type list (click to edit)
│   │   └── add_edit_type.html  # Add/edit type form
│   └── static/
│       ├── css/
│       │   ├── themes.css      # 7 themes with CSS variables
│       │   ├── shared.css      # Common styles, buttons, forms
│       │   ├── main_view.css   # Main view specific
│       │   ├── pickers.css     # Date picker components
│       │   ├── settings.css    # Settings page
│       │   ├── backups.css     # Backups page
│       │   └── manage_types.css # Type management
│       ├── js/
│       │   ├── main_view.js    # Search, charts, drag-drop, etc.
│       │   └── pickers.js      # Date picker logic
│       └── fonts/              # Local font files
├── data/
│   └── libram.db               # SQLite database (gitignored)
└── backups/                    # Backup files (gitignored)
```

---

## Theme System

Seven themes defined in `themes.css`:
1. **Quiet Sky** (purple/lavender) - default
2. **Gentle Dawn** (pink/rose)
3. **Warm Ember** (amber/orange)
4. **Garden Path** (green/sage)
5. **Deep Water** (teal/cyan)
6. **Soft Earth** (brown/tan)
7. **Evening Ritual** (dark mode)

CSS variables used throughout: `--bg-primary`, `--bg-secondary`, `--bg-card`, `--text-primary`, `--text-muted`, `--accent-primary`, `--border-color`, etc.

---

## Book Types Feature

- Database table: `book_types` (id, name, color, sort_order)
- Each book has optional `type_id` foreign key
- Type badges display with background color and dark gray text (#374151)
- Manage Types page: clickable rows (EdgeCase pattern)
- Add/Edit Type: grid color picker with checkmarks
- "By Type" chart: horizontal bars showing top 6 types by count

---

## Main View Features

- **Two view modes**: Detailed (table-like) and Compact (card-like)
- **Three chart views**: Books/Month, Pg/Day distribution, By Type
- **Collapsible year sections**: Current year expanded by default
- **Draggable stat cards**: Order saved to database
- **Instant search**: Client-side filtering by title/author
- **Rating stars**: Colored by tier (customizable 5-star and 1-star colors)

---

## Recent Commits (this session)

1. `7907968` - Add backups/ to gitignore, remove accidental backup file
2. `0a696d0` - UI polish for Evening Ritual theme compatibility
3. `480ff72` - Add instant search-as-you-type filtering
4. `59d0c3e` - Remove SQLCipher encryption, use plain SQLite
5. `85ac041` - Narrow metadata columns in detailed view for more title space
6. `d19381c` - Improve type management UI and add By Type chart

---

## Known Patterns & Conventions

- **EdgeCase patterns**: Click-to-edit rows, form-card structure, section headers
- **Button styles**: `btn-primary` (accent), `btn-secondary` (theme-aware neutral), `btn-danger`
- **Theme compatibility**: Always use CSS variables, never hardcode colors
- **Form groups**: `.form-group` with label and input, max-width: 350px in settings
- **Type badges**: Background color from type, text always #374151

---

## Next Steps / TODO

- Deploy to home server with Tailscale access
- Consider production WSGI server (gunicorn) for deployment
- Any additional UI polish or features Richard wants to add

---

## Server Commands

```bash
# Start server (from /Users/rick/libram)
source venv/bin/activate && python main.py

# Server runs at http://127.0.0.1:8090
# Debug mode on - auto-reloads on file changes
```
