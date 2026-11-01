# Changelog

All notable changes to Libram, organized by date.

---

## November 1, 2026 — Auto-Growing Notes Field, Unsaved-Changes Warning

### Improvements
- The Notes field on the add/edit book form now grows to fit its content, both on load and while typing, so long notes are visible in full without scrolling inside the box (100px minimum height retained)
- Leaving the add/edit book form with unsaved changes now asks first: Cancel opens an "Unsaved Changes" modal (Stay Here / Leave Without Saving); closing the tab, reloading, or browser Back gets the browser's native prompt. Save and Delete never prompt
- On the edit form, Save is greyed out and reads "No Changes" until something actually changes (edit-then-undo returns it to "No Changes")

### Implementation
- Inline auto-resize handler in `book_form.html` (sets height from `scrollHeight` plus border width on `input` and window `resize`)
- `overflow-y: hidden` on `.form-group textarea` in `shared.css` to prevent scrollbar flash during resize
- New `static/js/form-guard.js`, ported from EdgeCase (leave protection plus dirty-state Save button via `[data-dirty-save]`). Async cover upload / ISBN lookup dispatch `form-guard:refresh` since their writes fire no events. Generic `.btn:disabled` style added to `shared.css`. Opt-in via `<form data-dirty-guard>`; snapshot-and-compare dirty detection so programmatic picker writes and edit-then-undo are handled. Loaded after the page's inline init so the baseline is taken after the date pickers set their initial values, with a re-baseline at window `load` if the user hasn't touched the form

---

## August 26, 2026 — Books by Rating Chart

### Features
- Add a "By Rating" view to the dashboard chart card (toggles in after "By Type")
- All-time book counts for the five rating tiers, ordered 5 (best) to 1, each bar in its rating tier's color (custom 5/1 colors and names from settings carry through)
- Unrated books (rating 0, including in-progress books) are excluded; all five tiers are always shown, even at zero

### Implementation
- `get_books_by_rating_stats()` in `core/database.py` returns fixed-order tier counts
- New `/api/books-by-rating` endpoint resolves tier display names (`rating_5_name`/`rating_1_name` settings, Gold/Silver/Bronze fixed)
- `renderRatingsChart()` renderer reuses the By Type horizontal bar layout; tier colors read from `--rating-5-star`/`--rating-1-star` CSS variables with the same fallbacks as the rating star classes

---

## June 20, 2026 — Pages Per Month Chart

### Features
- Add a "Pages Per Month" view to the dashboard chart card (toggles in after "Books Per Month")
- Each book's pages are distributed across the calendar months its reading spanned, proportional to the days in each month — a book read 25% in June and 75% in July contributes pages to both months in that ratio, rather than dumping the whole total into the finish month

### Implementation
- `distribute_pages_across_months()` pure helper in `core/database.py` (unit-tested, no DB required)
- `get_pages_per_month()` aggregates attributed pages into the last 12 monthly buckets; in-progress books are excluded (final page count unknown), DNF books contribute `pages_completed`
- New `/api/pages-per-month` endpoint and `renderPagesPerMonthChart()` renderer

### Testing
- Add `test_pages_per_month.py` covering single-month, 25/75 split, multi-month, single-day, year-boundary, and sum-invariant cases

---

## February 15, 2026 — Backup System Improvements

### Backup Retention
- Fix: Retention cleanup now runs on every logout, not just when settings change or backups are created
- This ensures old backups are pruned even if the user doesn't actively create new ones
- Safety: Always keeps at least one backup chain, even if it exceeds retention period

### UI Cleanup
- Remove download button from backup restore points (users who need raw files can access the backups folder directly)

### Testing
- Add `test_cleanup.py` script to verify backup retention logic

---

## February 6, 2026 — Security Audit & Performance

### Security
- Auto-generate and persist Flask secret key to `data/.secret_key`
- Upgrade password hashing from unsalted SHA-256 to PBKDF2-HMAC-SHA256 (600k iterations, random salt)
- Legacy password hashes auto-migrate on login
- Validate settings API inputs against allowed values (theme, font, size, border, timeout, card order)

### Performance
- Cover thumbnails: pre-generate 300px JPEG thumbnails for fast compact view loading
- Fortunes migrated from 1684-line Python source to lazy-loaded JSON file
- N+1 query on types page replaced with single GROUP BY query

### Database
- Enable WAL journal mode for concurrent read/write support
- Checkpoint WAL before all backup operations (manual and auto)

### Cleanup
- Remove dead `export_csv` route from books blueprint (exports blueprint handles this)
- Remove dead `_get_date_options()` helper and all call sites

---

## January 21, 2026

- Replace Status column with Books count in Manage Types
- Narrow Manage Types page to 600px

---

## January 8, 2026

- Fix book form button alignment and remove redundant Back button
- Fix compact view cover vertical alignment
- Remove duplicate `.form-actions` from add_edit_type.css

---

## January 6, 2026

- Add logout modal with spinner animation
- Add heartbeat monitoring for desktop mode (`LIBRAM_DESKTOP=1`)

---

## January 1, 2026

- Move auto-backup from login to logout/shutdown
- Move book count next to year in year headers
- Skip backup if database unchanged since last backup

---

## December 25, 2025

- Add hidden username field for password manager compatibility

---

## December 23, 2025

- Force compact view on iPad Mini and smaller devices
- Column header bar styling (shadow, removed border)
- Change auto-backup to calendar-based scheduling (Every Session / Daily / Weekly / Manual)

---

## December 22, 2025

### Theme Overhaul
- Replace Grimoire/Wasteland/Lost World with Ink/Slate/Parchment
- Simplify to 6 themes (3 light, 3 dark), make Ink the default
- Restyle login, setup, and about modal to match Ink theme
- Add logo image to login and setup pages

### Other
- Markdown export: add Compact/Detailed style toggle, include notes in compact format
- Fix corrupted font files (Lora, Literata, Libre Baskerville)
- Backups: add cloud folder detection (iCloud, Dropbox, Google Drive, OneDrive)
- Convert Settings and Backups native selects to custom dropdowns
- Force font inheritance on form elements

---

## December 20–21, 2025

- ISBN lookup now auto-populates title, author, pages, and cover
- Add theme-specific danger/delete button colors
- Transparent logo backgrounds (login + about modal)
- Fix hardcoded paths to be relative to app root
- Remove unused imports (ruff cleanup)

---

## December 17–18, 2025

- Add Terminal dark theme, rename old Terminal to Nautilus
- Convert Crimson Veil and Hardboiled to dark themes
- Make Witching Hour the default theme
- Theme-aware empty state banner
- Normalize ISBN on save (strip hyphens and spaces)
- Add user guide documentation
- Fix user backgrounds sync

---

## December 16, 2025 — v1.0 Release

- Responsive design for phones and tablets
- Consolidate database schema (remove inline migrations)
- Switch to Waitress production server
- Code audit and cleanup
- Add type hints to core modules and blueprints
- Add packaging files and documentation

---

## December 15, 2025

- Cover art system with Open Library ISBN search and manual upload
- Sun/moon sign display in fortune bar (with toggle in Settings)
- Replace alerts with modals in book form
- Session timeout warning system with countdown modal
- Fix fortune bar layout for long quotes

---

## December 14, 2025

- Fortune bar with 1,666 quotes, shown per session
- Export page with CSV and Markdown formats, date range filtering
- Auto-backup settings with frequency and retention
- Subtitle field for books
- Enhanced DNF feature: pages read field, auto-set date finished
- Border Style setting (Accent vs Vibrant)

---

## December 13, 2025

- Remove SQLCipher encryption, use plain SQLite
- Instant search-as-you-type filtering
- Genre-based theme names (Grimoire, Crimson Veil, etc.)
- Theme palette enrichment: saturated accents, tinted cards
- Gradient backgrounds and accent borders
- Restyle login page (dark glassmorphism)

---

## December 11, 2025

- Book types feature with management UI and color badges
- By Type chart in dashboard

---

## December 9, 2025

- New book/star logo and favicons
- About modal

---

## December 7–8, 2025

- Comprehensive theme system (8 themes)
- Font options (5 families) and S/M/L size selector
- Customizable rating colors (1-star and 5-star)
- Switch from Lucide to Phosphor icons
- Simplify info cards to 3 (Pages, Chart, Navigation)
- Compact view book card layout redesign

---

## December 6, 2025 — Project Start

- Initial commit: book tracking, dual numbering, password protection
- Custom background upload
- Font selector, port 8090
- Books Per Month chart
