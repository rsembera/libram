# Libram 📚

**Personal Reading Tracker**

A web-based reading tracker designed for personal use, with plans for Raspberry Pi deployment.

## Features

- **Track your reading** - Log books with title, author, pages, dates, and ratings
- **Automatic calculations** - Days to complete, pages per day
- **Year-over-year tracking** - Books grouped by year with dual numbering system
- **Multiple view modes** - Detailed (horizontal) and Compact (stacked) layouts
- **Dashboard stats** - Total books, books this year, pages read, average pace
- **Customizable themes** - 5 card color schemes, 4 background options
- **Encrypted database** - SQLCipher encryption for privacy
- **Password protected** - Secure access with session timeout
- **CSV export** - Export your complete reading history
- **Backup system** - Manual backups with restore capability

## Rating System

- ☆ No rating
- ★ Black
- ★ Bronze  
- ★ Silver
- ★ Gold
- ★ Green

## Installation

### Requirements

- Python 3.10+
- SQLCipher (for database encryption)

### Setup

```bash
# Clone or download
cd ~/libram

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

The app will open in your browser at `http://127.0.0.1:8080`

### First Run

On first run, you'll be prompted to create a master password. This protects access to your reading database.

## Usage

### Adding Books

1. Click **Add Book** from the main view
2. Fill in title, author, pages
3. Set the date you began reading
4. When finished, add the completion date
5. Optionally add a rating and notes

### Year Assignment

Books belong to the year they were **begun**, not finished. A book started December 28, 2024 belongs to 2024 even if finished in January 2025.

### Keyboard Shortcuts

- `/` - Focus search box
- `Escape` - Clear search / Close modal

## Deployment

### Raspberry Pi

For 24/7 access on your home network:

```bash
# Set host to allow network access
export LIBRAM_HOST=0.0.0.0
export LIBRAM_PORT=8080
python main.py
```

Access from other devices at `http://raspberry-pi-ip:8080`

### Security Note

When exposing to a network, ensure your password is strong. Consider using a reverse proxy (nginx/Caddy) with HTTPS for internet access.

## Data Storage

- **Database**: `~/libram/data/libram.db`
- **Backups**: `~/libram/backups/`

## Technology

- **Backend**: Python 3, Flask
- **Database**: SQLite with SQLCipher encryption
- **Frontend**: Vanilla JavaScript, Lexend font, Lucide icons
- **No build step**: Edit and reload

## Credits

Designed by Richard Sembera  
Built with Claude

---

*"Every book is an edge case."*
