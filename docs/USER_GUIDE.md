# Libram User Guide

**Version 1.1** — February 2026

Libram is a personal reading tracker. It helps you log the books you read, track your reading pace, and look back on your reading history over the years.

---

## Getting Started

### First Launch

When you first open Libram, you'll be asked to create a password. This protects access to your reading data. After that, you'll land on the main dashboard.

### The Main View

The main view shows:

- **Info Cards** — Three draggable cards at the top: Pages (this year + lifetime), Reading Chart, and Navigation
- **Fortune Bar** — Today's date, optional astrology, and a random quote
- **Your Books** — Grouped by year, with the current year expanded by default

You can switch between **Detailed** view (horizontal book cards with full info) and **Compact** view (stacked layout, better for long lists).

---

## Adding Books

Click **Add Book** to log a new book. Fill in:

- **Title** and **Subtitle** (optional)
- **Author**
- **Pages** — Total page count
- **Date Begun** — When you started reading
- **Date Finished** — Leave blank if still reading
- **Type** — Fiction, Non-Fiction, or custom types you've created
- **Rating** — Optional 1-5 star rating
- **Notes** — Any thoughts or comments

### Cover Art

You can add cover art two ways:

1. **ISBN Lookup** — Enter the ISBN and click the search icon. Libram fetches the cover, title, author, and page count from Open Library (only populates empty fields).
2. **Upload** — Click "Upload" to add your own image.

### Did Not Finish (DNF)

Check the DNF box if you abandoned a book. You can optionally record how many pages you completed. DNF books show with an empty star (☆) and don't count toward your reading stats.

### Days Paused

If you took a break mid-book (vacation, busy period), enter the number of days paused. This adjusts your pages-per-day calculation to reflect actual reading time.

---

## Book Numbering

Every book gets two numbers:

- **All-Time #** — Your lifetime book count (e.g., #347)
- **Yearly #** — Count within the year (e.g., #12 for 2025)

**Year assignment is based on when you began the book**, not when you finished. A book started December 28, 2024 belongs to 2024 even if you finish it in January 2025.

---

## Editing and Deleting Books

Click on any book card to open it for editing. Make your changes, then click **Save Changes**.

To delete a book, click the **Delete** button at the bottom of the edit page. You'll be asked to confirm.

---

## Search

Type in the search box to filter your books. Search matches against title and author. The filter applies across all years.

Click the X button to clear the search.

---

## Book Types

Book types let you categorize your reading. Libram comes with Fiction and Non-Fict (9-character limit), but you can create your own.

Go to **Settings → Manage Book Types** to add, edit, or delete types. Each type has a color that appears as a badge on book cards.

---

## Settings

Access Settings from the Navigation card on the main view.

### Appearance

- **Theme** — Six color themes in two families:
  - **Light:** Ink (default), Slate, Parchment
  - **Dark:** Witching Hour, Crimson Veil, Terminal
- **Background** — Solid colors or upload a custom background image
- **Font** — Choose from Lexend, Libre Baskerville, Lora, Source Sans 3, or Literata
- **Font Size** — Small, Medium, or Large
- **Border Style** — Accent colored borders or subtle gray

### Rating Colors

Customize the colors for your 1-star and 5-star ratings. Ratings 2-4 (bronze, silver, gold) are fixed. Choose from colors like Black, Green, Blue, Purple, and more.

### Show Astrology

Toggle sun/moon sign display in the fortune bar.

### Dashboard Layout

Rearrange the three info cards. On desktop you can also drag them directly.

### Security

- **Change Password** — Update your login password
- **Session Timeout** — Auto-logout after inactivity (15 min to 2 hours, or never)

---

## Export

Go to **Export** to download your reading data.

**Formats:**

- **CSV** — Spreadsheet-compatible, good for analysis or backup
- **Markdown** — Human-readable, good for sharing or printing

**Options:**

- **Date Range** — Export all books or filter by start/end date
- **Order** — Newest first or oldest first

---

## Backup

Go to **Backup** to manage your data backups.

### Manual Backup

Click **Create Backup Now** to save a snapshot of your database.

### Auto-Backup

Enable automatic backups with your preferred frequency and retention period:

- **Frequency:** Every Session, Daily, Weekly, or Manual Only
- **Retention:** 1 Month, 6 Months, 1 Year, or Forever
- **Location:** App folder (default) or a detected cloud folder (iCloud, Dropbox, Google Drive, OneDrive)

Backups are created on logout and app shutdown. If the database hasn't changed since the last backup, it's skipped.

### Restore

To restore from a backup, click the restore icon next to any backup file. This replaces your current data with the backup — use with caution.

### Download

You can also download backup files to your computer for safekeeping.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Escape` | Close cover image lightbox |

---

## Data Storage

All your data stays on your machine:

- **Database** — `data/libram.db`
- **Cover images** — `covers/` (thumbnails in `covers/thumbs/`)
- **Backups** — `backups/` (or cloud folder if configured)
- **Custom backgrounds** — `web/static/user_backgrounds/`

Nothing is sent to the cloud. Your reading history is yours.

---

## Tips

- **Track DNF honestly** — It's useful to know which books you abandoned and why
- **Use Days Paused** — If life interrupts a book, log it so your pace stats stay meaningful
- **Explore themes** — Each theme changes the entire mood of the app
- **Regular backups** — Enable auto-backup for peace of mind

---

## Running Libram

**Normal mode (production):**
```bash
python main.py
```

**Development mode (auto-reloads on code changes):**
```bash
python main.py --debug
```

**Environment variables:**
- `LIBRAM_HOST` — Bind address (default: `127.0.0.1`)
- `LIBRAM_PORT` — Port (default: `8090`)
- `LIBRAM_BROWSER=1` — Auto-open browser on start

---

*Happy reading!* 📚
