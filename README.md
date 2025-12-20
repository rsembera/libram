# Libram 📚

**Personal Reading Tracker**

A clean, self-hosted web app to track your reading history. Designed for personal use on your local machine or a home server like a Raspberry Pi.

## Features

- **Track your reading** — Log books with title, subtitle, author, pages, dates, and ratings
- **Automatic calculations** — Days to complete, pages per day
- **Year-over-year tracking** — Books grouped by year with dual numbering (all-time + yearly)
- **Book types** — Categorize books (Fiction, Non-Fiction, or custom types)
- **Cover art** — Fetch covers and book info via ISBN from Open Library, or upload your own
- **Multiple views** — Detailed (horizontal cards) and Compact (stacked) layouts
- **Dashboard stats** — Draggable info cards with reading charts
- **8 color themes** — Witching Hour, Crimson Veil, Hardboiled, Terminal, Grimoire, Wasteland, Lost World, Nautilus
- **Custom backgrounds** — Solid colors or upload your own images
- **DNF tracking** — Mark books as "Did Not Finish" with pages completed
- **Fortune bar** — Daily quotes with optional sun/moon astrology signs
- **Export** — CSV or Markdown with date range filtering
- **Auto-backup** — Configurable automatic backups with retention settings
- **Password protected** — Secure access with configurable session timeout
- **Responsive design** — Works on desktop, tablet, and phone

## Rating System

Customizable 5-tier rating system (default names):
- ☆ No rating
- ★ Black
- ★ Bronze  
- ★ Silver
- ★ Gold
- ★ Green

## Installation

### Requirements

- Python 3.10+

### Setup

```bash
# Clone the repository
git clone https://github.com/rsembera/libram.git
cd libram

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run (production mode with Waitress)
python main.py

# Or run in development mode (auto-reload)
python main.py --debug
```

The app runs at `http://127.0.0.1:8090`

### First Run

On first launch, you'll be prompted to create a password. This protects access to your reading tracker.

## Usage

### Adding Books

1. Click **Add Book** from the main view
2. Fill in title, author, pages
3. Optionally add ISBN (auto-fills title, author, pages, and cover), or upload a cover
4. Set the date you began reading
5. When finished, add the completion date
6. Add a rating and notes if desired

### Year Assignment

Books belong to the year they were **begun**, not finished. A book started December 28, 2024 belongs to 2024 even if finished in January 2025.

### Keyboard Shortcuts

- `/` — Focus search box
- `Escape` — Clear search / Close modals

## Deployment

### Home Server / Raspberry Pi

For 24/7 access on your home network:

```bash
export LIBRAM_HOST=0.0.0.0
export LIBRAM_PORT=8090
python main.py
```

Access from other devices at `http://your-server-ip:8090`

### Environment Variables

- `LIBRAM_HOST` — Bind address (default: `127.0.0.1`)
- `LIBRAM_PORT` — Port number (default: `8090`)
- `LIBRAM_DEBUG` — Set to `1` for development mode
- `LIBRAM_BROWSER` — Set to `1` to auto-open browser on start

## Data Storage

- **Database**: `data/libram.db` (SQLite)
- **Covers**: `covers/`
- **Backups**: `backups/`
- **Custom backgrounds**: `web/static/backgrounds/`

## Technology

- **Backend**: Python 3, Flask, Waitress
- **Database**: SQLite
- **Frontend**: Vanilla JavaScript, CSS custom properties
- **Fonts**: Lexend, Libre Baskerville, Lora, Source Sans 3, Literata
- **Icons**: Phosphor Icons

## License

MIT License — see [LICENSE](LICENSE) for details.

## Credits

Designed by Richard Sembera  
Built with Claude

---

*"A libram for every reader."*
