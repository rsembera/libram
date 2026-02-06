"""
Libram Thumbnail Generator
Generates and serves pre-sized cover thumbnails for fast list views.
Gracefully degrades to serving originals if Pillow is unavailable.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

THUMB_HEIGHT = 300  # pixels — plenty for 145px CSS display
THUMB_QUALITY = 85  # JPEG quality

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    logger.info("Pillow not installed — thumbnails disabled, serving originals")


def get_thumbs_dir(covers_dir: str) -> Path:
    """Get the thumbnails subdirectory, creating it if needed."""
    thumbs = Path(covers_dir) / 'thumbs'
    thumbs.mkdir(exist_ok=True)
    return thumbs


def generate_thumbnail(covers_dir: str, filename: str) -> str | None:
    """Generate a JPEG thumbnail for a cover image.
    
    Returns the thumbnail filename (always .jpg), or None if generation fails.
    """
    if not HAS_PILLOW:
        return None

    source = Path(covers_dir) / filename
    if not source.exists():
        return None

    # Thumbnail is always JPEG, regardless of source format
    thumb_name = Path(filename).stem + '_thumb.jpg'
    thumb_path = get_thumbs_dir(covers_dir) / thumb_name

    try:
        with Image.open(source) as img:
            # Convert to RGB (handles RGBA PNGs, palette images, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            # Only shrink, never enlarge
            if img.height > THUMB_HEIGHT:
                ratio = THUMB_HEIGHT / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, THUMB_HEIGHT), Image.LANCZOS)

            img.save(thumb_path, 'JPEG', quality=THUMB_QUALITY, optimize=True)
            return thumb_name
    except Exception as e:
        logger.warning(f"Failed to generate thumbnail for {filename}: {e}")
        return None


def get_thumbnail_path(covers_dir: str, filename: str) -> str | None:
    """Get path to existing thumbnail, or None if it doesn't exist."""
    if not filename:
        return None
    thumb_name = Path(filename).stem + '_thumb.jpg'
    thumb_path = get_thumbs_dir(covers_dir) / thumb_name
    if thumb_path.exists():
        return str(thumb_path)
    return None


def delete_thumbnail(covers_dir: str, filename: str) -> None:
    """Delete a thumbnail if it exists."""
    if not filename:
        return
    thumb_name = Path(filename).stem + '_thumb.jpg'
    thumb_path = Path(covers_dir) / 'thumbs' / thumb_name
    if thumb_path.exists():
        try:
            thumb_path.unlink()
        except Exception:
            pass


def generate_missing_thumbnails(covers_dir: str) -> int:
    """Generate thumbnails for all covers that don't have one yet.
    
    Returns the number of thumbnails generated.
    """
    if not HAS_PILLOW:
        return 0

    covers = Path(covers_dir)
    if not covers.exists():
        return 0

    count = 0
    allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

    for f in covers.iterdir():
        if not f.is_file() or f.suffix.lower() not in allowed:
            continue
        # Check if thumb already exists
        if get_thumbnail_path(covers_dir, f.name) is None:
            if generate_thumbnail(covers_dir, f.name):
                count += 1

    if count:
        logger.info(f"Generated {count} missing thumbnail(s)")
    return count
