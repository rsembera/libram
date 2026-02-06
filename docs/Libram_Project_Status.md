# Libram Project Status

**Last Updated:** February 6, 2026  
**Repository:** https://github.com/rsembera/libram  
**Project Started:** December 6, 2025

---

## Overview

Libram is a personal reading tracker — a self-hosted Flask web app for logging books, tracking reading pace, and reviewing reading history over time. Designed for local use on a home server.

---

## Features (Complete)

### Core Functionality
- **Book tracking** — Title, subtitle, author, pages, dates begun/finished, rating, notes
- **ISBN lookup** — Auto-populates title, author, pages, and cover from Open Library
- **Cover art** — Fetch via ISBN or upload manually; thumbnails generated for fast list views
- **Dual numbering** — All-time # and yearly # (year assigned by date begun)
- **DNF tracking** — "Did Not Finish" with pages completed
- **Days paused** — Adjusts pace calculations for reading breaks
- **Book types** — User-defined categories with custom colors (default: Fiction, Non-Fiction)

### Views & Navigation
- **Main view** — Books grouped by year → month, current year expanded
- **Detailed view** — Horizontal cards with full info
- **Compact view** — Stacked layout for long lists
- **Dashboard cards** — Draggable info cards (Pages, Reading Chart, Navigation)
- **Search** — Filter by title and author

### Theming System (8 themes)
**Dark themes:**
- Witching Hour (default) — Dark blue/purple, horror/gothic
- Crimson Veil — Deep blacks with blood red, dark romance
- Terminal — Green on black, classic CRT monochrome
- Hardboiled — Dark smoky grays with amber, noir/detective

**Light themes:**
- Grimoire — Purple/lavender, fantasy/magic
- Wasteland — Amber/orange, post-apocalyptic
- Lost World — Green/sage, adventure/expedition
- Nautilus — Teal/cyan, underwater/adventure

### Customization
- **Custom backgrounds** — Solid colors or uploaded images
- **Font selection** — Lexend, Libre Baskerville, Lora, Source Sans 3, Literata
- **Font sizes** — Small, Medium, Large
- **Border styles** — Accent colored or subtle gray
- **Rating colors** — Customizable 1-star and 5-star colors

### Data Management
- **Export** — CSV or Markdown with date range filtering
- **Auto-backup** — Configurable frequency (every session/daily/weekly/manual) with retention
- **Manual backup** — Create and download on demand
- **Cloud backup** — Auto-detects iCloud, Dropbox, Google Drive, OneDrive
- **Restore** — Restore from any backup file (pre-restore backup created automatically)

### Security
- **Password protection** — PBKDF2-HMAC-SHA256 hashed (600k iterations, random salt)
- **Auto-generated secret key** — Persisted to `data/.secret_key` (0o600 permissions)
- **Session timeout** — Configurable with frontend warning system
- **Input validation** — Settings API validates against allowed values

### Other
- **Fortune bar** — Daily quotes with optional sun/moon astrology signs
- **Responsive design** — Works on desktop, tablet, phone
- **Cover thumbnails** — Pre-generated 300px JPEG thumbnails for fast list loading

---

## Technical Stack

### Backend
- Python 3.10+
- Flask 3.x
- Waitress (production server)
- SQLite database (WAL mode, foreign keys enabled)

### Frontend
- Vanilla JavaScript
- CSS custom properties (theming)
- Phosphor Icons

### Dependencies
```
flask>=3.0.0
ephem           # Astrology calculations
waitress>=3.0.0 # Production server
requests>=2.28.0 # ISBN/cover lookup
Pillow>=10.0.0  # Cover thumbnail generation
```

---

## File Structure

```
libram/
├── main.py                 # Entry point
├── requirements.txt
├── core/
│   ├── database.py         # Database operations, migrations
│   ├── astrology.py        # Sun/moon sign calculations
│   ├── fortunes.py         # Lazy-loaded random quotes
│   ├── fortunes.json       # Fortune text data (1,666 entries)
│   └── thumbnails.py       # Cover thumbnail generation
├── web/
│   ├── app.py              # Flask app factory
│   ├── blueprints/
│   │   ├── auth.py         # Login, logout, password
│   │   ├── books.py        # Add, edit, delete books
│   │   ├── covers.py       # Cover upload, ISBN search, thumbnails
│   │   ├── settings.py     # App settings (validated inputs)
│   │   ├── types.py        # Book type management
│   │   ├── exports.py      # CSV/Markdown export
│   │   └── backups.py      # Backup/restore (WAL checkpoint before copy)
│   ├── static/
│   │   ├── css/            # 11 CSS files including themes.css
│   │   ├── js/             # 4 JS files
│   │   ├── fonts/
│   │   ├── backgrounds/    # Default backgrounds
│   │   └── user_backgrounds/ # User uploads (gitignored)
│   └── templates/          # 11 Jinja2 templates
├── data/
│   ├── libram.db           # SQLite database (WAL mode)
│   └── .secret_key         # Auto-generated Flask secret key
├── covers/                 # Downloaded/uploaded covers
│   └── thumbs/             # Auto-generated JPEG thumbnails
├── backups/                # Database backups
└── docs/
    └── Libram_Project_Status.md
```

---

## Database

### Schema

#### books
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| title | TEXT | Book title |
| subtitle | TEXT | Optional subtitle |
| author | TEXT | Author name(s) |
| pages | INTEGER | Total page count |
| pages_completed | INTEGER | For DNF books |
| date_begun | INTEGER | Unix timestamp |
| date_finished | INTEGER | Unix timestamp (null if reading) |
| days_paused | INTEGER | Days not reading |
| rating | INTEGER | 0-5 stars |
| did_not_finish | INTEGER | Boolean (0/1) |
| notes | TEXT | User notes |
| type_id | INTEGER | FK to book_types |
| cover_filename | TEXT | Filename in covers/ |
| isbn | TEXT | Normalized ISBN |
| all_time_number | INTEGER | Lifetime book count |
| yearly_number | INTEGER | Year-specific count |
| created_at | INTEGER | Unix timestamp |
| modified_at | INTEGER | Unix timestamp |

#### book_types
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Type name (unique, 9 char max) |
| color | TEXT | Badge color (hex) |
| bubble_color | TEXT | Background tint (hex) |
| created_at | INTEGER | Unix timestamp |
| modified_at | INTEGER | Unix timestamp |

#### settings
| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | Primary key |
| value | TEXT | Setting value |
| modified_at | INTEGER | Unix timestamp |

### Database Practices
- **WAL mode** — Enabled for concurrent read/write support
- **Foreign keys** — Enabled via PRAGMA
- **Checkpoint** — Called before all backup operations
- **Password storage** — `pbkdf2:600000:<salt_hex>:<hash_hex>` format
  - Legacy SHA-256 hashes auto-migrate on login

---

## Deployment

### Target Environment
- **Server:** Sentinel (ACEMAGIC V1 Mini PC)
- **Specs:** Intel N150, 16GB RAM, 512GB SSD, Debian 13
- **Access:** Tailscale VPN at `100.116.129.95`
- **Port:** 8090

### First-Time Setup
```bash
ssh rick@100.116.129.95
cd ~/Applications
git clone https://github.com/rsembera/libram.git
cd libram
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Systemd Service
File: `/etc/systemd/system/libram.service`
```ini
[Unit]
Description=Libram Reading Tracker
After=network.target

[Service]
User=rick
WorkingDirectory=/home/rick/Applications/libram
Environment="LIBRAM_HOST=0.0.0.0"
Environment="LIBRAM_PORT=8090"
ExecStart=/home/rick/Applications/libram/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable libram
sudo systemctl start libram
```

### Updates
```bash
ssh rick@100.116.129.95
cd ~/Applications/libram && git pull && sudo systemctl restart libram
```

### Access
- URL: `http://100.116.129.95:8090` (via Tailscale)

---

## Backup Strategy

- **Auto-backup:** Configured in app (frequency + retention)
- **Location:** `/home/rick/Applications/libram/backups/` on Sentinel
- **Cloud:** Optional sync to iCloud, Dropbox, Google Drive, or OneDrive
- **Redundancy:** Syncthing syncs backups to MacBook Air M4
- **WAL checkpoint** — Always performed before backup copy

---

## Security Audit (February 6, 2026)

Comprehensive security review cross-referencing known vulnerabilities from Synesius and EdgeCase projects:

| Issue | Status |
|-------|--------|
| Hardcoded secret key fallback | ✅ Fixed — auto-generated, persisted to `data/.secret_key` |
| Unsalted SHA-256 password hash | ✅ Fixed — upgraded to PBKDF2-HMAC-SHA256 (600k iterations) |
| Session race condition (Safari/Firefox double-login) | ✅ Already fixed (all four Flask session fixes present) |
| WAL mode not enabled | ✅ Fixed — `PRAGMA journal_mode = WAL` in `connect()` |
| Backup without WAL checkpoint | ✅ Fixed — `checkpoint()` before all backup copies |
| Settings API input validation | ✅ Fixed — allowlists for theme, font, size, border, timeout |
| N+1 query on types page | ✅ Fixed — single `GROUP BY` query |
| Fortunes loaded at import time (157KB) | ✅ Fixed — lazy-loaded from JSON |
| Dead code (unused export route, helper) | ✅ Removed |

---

## Development Status

### Current Phase
**Active use** — Running on Sentinel since December 2025

### Planned
- [ ] Cover art integration improvements
- [ ] Responsive design refinements
- [ ] Consider TUI/console interface

---

## Recent Changes

| Date | Change |
|------|--------|
| Feb 6, 2026 | Security audit: secret key, PBKDF2 passwords, WAL mode, backup checkpoint |
| Feb 6, 2026 | Cover thumbnails for fast compact view loading |
| Feb 6, 2026 | Fortunes migrated to lazy-loaded JSON |
| Feb 6, 2026 | Settings input validation, N+1 fix, dead code cleanup |
| Jan 2026 | Ongoing use and minor fixes |
| Dec 20, 2025 | ISBN lookup, auto-backup, export system, 8 themes |
| Dec 6, 2025 | Project started |

---

## Related Projects

- **EdgeCase Equalizer** — Therapy practice management (Flask, source of session fix pattern)
- **Synesius** — Dream journal with RAG analysis (Flask/SQLCipher, source of security patterns)

---

*"A libram for every reader."*
