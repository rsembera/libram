# Libram Project Status

**Last Updated:** December 20, 2025  
**Repository:** https://github.com/rsembera/libram  
**Current Commit:** `2601de7` (79 commits total)  
**Project Started:** December 6, 2025

---

## Overview

Libram is a personal reading tracker — a self-hosted Flask web app for logging books, tracking reading pace, and reviewing reading history over time. Designed for local use on a home server.

---

## Features (Complete)

### Core Functionality
- **Book tracking** — Title, subtitle, author, pages, dates begun/finished, rating, notes
- **ISBN lookup** — Auto-populates title, author, pages, and cover from Open Library
- **Cover art** — Fetch via ISBN or upload manually
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
- **Auto-backup** — Configurable frequency (daily/weekly/monthly) and retention
- **Manual backup** — Create and download on demand
- **Restore** — Restore from any backup file

### Other
- **Fortune bar** — Daily quotes with optional sun/moon astrology signs
- **Password protection** — Secure access with configurable session timeout
- **Responsive design** — Works on desktop, tablet, phone

---

## Technical Stack

### Backend
- Python 3.10+
- Flask 3.x
- Waitress (production server)
- SQLite database

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
│   └── fortunes.py         # Random quotes
├── web/
│   ├── app.py              # Flask app factory
│   ├── blueprints/
│   │   ├── auth.py         # Login, logout, password
│   │   ├── books.py        # Add, edit, delete books
│   │   ├── covers.py       # Cover upload, ISBN search
│   │   ├── settings.py     # App settings
│   │   ├── types.py        # Book type management
│   │   ├── exports.py      # CSV/Markdown export
│   │   └── backups.py      # Backup/restore
│   ├── static/
│   │   ├── css/            # 11 CSS files including themes.css
│   │   ├── js/             # 4 JS files
│   │   ├── fonts/
│   │   ├── backgrounds/    # Default backgrounds
│   │   └── user_backgrounds/ # User uploads (gitignored)
│   └── templates/          # 11 Jinja2 templates
├── data/
│   └── libram.db           # SQLite database
├── covers/                 # Downloaded/uploaded covers
├── backups/                # Database backups (synced to MacBook via Syncthing)
└── docs/
    └── USER_GUIDE.md
```

---

## Database Schema

### books
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

### book_types
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Type name (unique) |
| color | TEXT | Badge color |
| bubble_color | TEXT | Background tint |
| created_at | INTEGER | Unix timestamp |
| modified_at | INTEGER | Unix timestamp |

### settings
| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | Primary key |
| value | TEXT | JSON-encoded value |
| modified_at | INTEGER | Unix timestamp |

---

## Deployment

### Target Environment
- **Server:** Sentinel (ACEMAGIC V1 Mini PC)
- **Specs:** Intel N150, 16GB RAM, 512GB SSD, Debian 13
- **Access:** Tailscale VPN at `100.116.129.95`

### First-Time Setup
```bash
ssh rick@100.116.129.95
cd ~
git clone https://github.com/rsembera/libram.git
cd libram
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Systemd Service
Create `/etc/systemd/system/libram.service`:
```ini
[Unit]
Description=Libram Reading Tracker
After=network.target

[Service]
User=rick
WorkingDirectory=/home/rick/libram
Environment="LIBRAM_HOST=0.0.0.0"
Environment="LIBRAM_PORT=8090"
ExecStart=/home/rick/libram/venv/bin/python main.py
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
cd ~/libram && git pull && sudo systemctl restart libram
```

### Access
- URL: `http://100.116.129.95:8090` (via Tailscale)

---

## Backup Strategy

- **Auto-backup:** Configured in app (frequency + retention)
- **Location:** `/home/rick/libram/backups/` on Sentinel
- **Redundancy:** Syncthing syncs backups to MacBook Air M4

---

## Development Status

### Current Phase
**Testing** — Month of personal use before public release

### Code Health (as of Dec 20, 2025)
- ✅ Linting clean (ruff)
- ✅ Type hints on core modules
- ✅ No dead code
- ~4,300 lines Python
- ~8,400 lines CSS
- ~2,300 lines JS (separate files + inline)

### Planned Before Public Release
- [ ] Month of real-world testing
- [ ] Aggressive refactor based on usage patterns
- [ ] Add type hints to Flask routes (if beneficial)
- [ ] Consider extracting inline JS
- [ ] Basic tests for database methods and date calculations
- [ ] Final documentation pass

---

## Recent Changes (December 2025)

| Date | Change |
|------|--------|
| Dec 20 | Delete button theming (dark vs light styles) |
| Dec 20 | ISBN lookup auto-populates title, author, pages |
| Dec 20 | Ruff cleanup (4 unused imports) |
| Dec 18 | Added Terminal dark theme, renamed old Terminal to Nautilus |
| Dec 18 | ISBN normalization on save |
| Dec 17 | Made Witching Hour default theme |
| Dec 17 | Converted Crimson Veil and Hardboiled to dark themes |
| Dec 17 | Setup screen restyled to match login |
| Dec 17 | Empty state banner theming |
| Dec 15 | Auto-backup system |
| Dec 14 | Export system (CSV/Markdown) |
| Dec 13 | Backup/restore system |

---

## Known Issues / Future Ideas

- None currently blocking

---

## Related Projects

- **Synesius** — Dream journal (cosmic aesthetic, fortune integration)
- **Basilinda Nova** — Sci-fi board game with CFR AI (planning stage)

---

*"A libram for every reader."*
