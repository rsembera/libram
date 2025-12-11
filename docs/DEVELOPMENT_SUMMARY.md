# Libram Development Summary — December 10, 2025

## Project Overview
**Libram** is a personal reading tracker web application built with Flask/Python, SQLite, and vanilla JavaScript. It replaces a manual Word document system with a searchable, theme-aware interface.

**Repository:** https://github.com/rsembera/libram  
**Local Path:** /Users/rick/libram  
**Port:** 8090  
**Current Version:** v1.0 Vance

---

## Completed Features

### Core Functionality
- Book CRUD operations with title, author, pages, dates, rating, notes
- Automatic calculations: days to read, pages/day
- Dual numbering system: all-time # and yearly # (year determined by date_begun)
- Days paused field for tracking reading breaks
- Year groupings with collapsible sections
- Compact and Detailed view modes
- Search/filter across books
- CSV export
- Local SQLite database

### Theme System (7 themes)
Implemented comprehensive CSS variable architecture with 30+ variables per theme:
1. **Quiet Sky** (purple/lavender) — default
2. **Gentle Dawn** (pink/rose)
3. **Warm Ember** (amber/orange)
4. **Garden Path** (green/sage)
5. **Deep Water** (teal/cyan)
6. **Soft Earth** (brown/tan)
7. **Evening Ritual** (dark mode, bg: #12141f)

Theme controls: backgrounds, cards, buttons, text, borders, accents, charts, book rows. Darkened page backgrounds for better card contrast. Added --divider-color and --chart-grid variables for visibility.

### Font System
5 local fonts (no external dependencies):
- Lexend (default)
- Libre Baskerville
- Lora
- Source Sans 3
- Literata

Font size selector: S (16px) / M (18px) / L (20px) — applied to `<html>` element so rem units scale proportionally.

### Rating System
- 5-star rating with customizable colors for 5-star and 1-star ratings
- 10 color presets in Settings
- Gold/silver/bronze fixed
- Custom dropdown in book form showing colored stars
- Rating colors stored as CSS variables

### UI Components
- Info cards: Total Books, Current Year stats, Pages (split layout with monthly averages)
- Chart toggle: Books/month vs Pages/day
- Navigation card buttons with Phosphor icons
- EdgeCase-style date pickers
- Custom dropdowns (theme, font, rating)
- Background image upload support

### Compact View Book Cards
```
#1 (Yr. #1)
★ Book Title
Author Name
289 pages • 2 days • 144 pg/day
Dec 05 → Dec 06
```

### About Modal (Settings page)
- Cosmic horror book creature logo
- "v1.0 Vance" (named after Jack Vance who invented the word "Libram")
- Credits: Designed by Richard Sembera, Coded by Claude Opus 4.5
- Motto: *"Some books read you back."*
- Dark-themed modal with purple accents

### Assets
- Favicon set: favicon.ico (multi-size), favicon-16.png, favicon-32.png, apple-touch-icon.png (180x180), icon-192.png
- About logo: /web/static/img/about-logo.png

### Authentication
- Password protection with Flask sessions
- Session timeout settings (15min to never)
- Flask double-login fix (from EdgeCase) applied

### Backup System
- Manual backup functionality
- Backup management page

---

## Project Structure
```
/Users/rick/libram/
├── main.py                 # Entry point
├── web/
│   ├── app.py              # Flask app setup, inject_theme_settings()
│   ├── blueprints/
│   │   ├── auth.py         # Login/logout, password
│   │   ├── books.py        # Book CRUD, CSV export
│   │   ├── settings.py     # Theme, font, font-size, rating-color endpoints
│   │   └── backups.py      # Backup management
│   ├── templates/
│   │   ├── base.html       # Font-size on html, rating colors inline
│   │   ├── main_view.html  # Book list, compact/detailed views
│   │   ├── book_form.html  # Add/edit book with custom rating dropdown
│   │   ├── settings.html   # All settings + About modal
│   │   └── ...
│   └── static/
│       ├── css/
│       │   ├── themes.css      # All 7 themes with CSS variables
│       │   ├── shared.css      # Fonts, common components, custom dropdowns
│       │   ├── main_view.css   # Book cards, charts, info cards
│       │   ├── settings.css    # Settings page + About modal styles
│       │   └── book_form.css   # Form styles, rating colors
│       ├── js/
│       │   ├── main_view.js    # Charts, view toggle, search
│       │   └── settings.js     # Theme/font/rating handlers, About modal
│       ├── fonts/              # All fonts local (Lexend, Libre Baskerville, Lora, Source Sans 3, Literata, Phosphor)
│       └── img/
│           ├── favicon.ico
│           ├── favicon-16.png
│           ├── favicon-32.png
│           ├── apple-touch-icon.png
│           ├── icon-192.png
│           └── about-logo.png
└── data/
    └── libram.db           # SQLite database
```

---

## Database Settings Keys
- `theme` — quiet-sky, gentle-dawn, warm-ember, garden-path, deep-water, soft-earth, evening-ritual
- `background_style` — empty (theme default) or uploaded image path
- `font_style` — lexend, libre-baskerville, lora, source-sans, literata
- `font_size` — s, m, l
- `rating_5_color` / `rating_5_name` — hex color and name for 5-star
- `rating_1_color` / `rating_1_name` — hex color and name for 1-star
- `session_timeout` — minutes (0 = never)

---

## Pending / Future Work
- **Mobile responsive design** — on the list for next session. Uses CSS media queries, no separate pages needed. Main changes: stack info cards, larger tap targets, possibly hide detailed view on mobile.

---

## Git Status
All changes committed and pushed to main branch. Clean working tree.

---

## To Start Development
```bash
cd /Users/rick/libram
source venv/bin/activate
python main.py
# Runs at http://127.0.0.1:8090
```
