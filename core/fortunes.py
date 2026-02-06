"""
Libram Fortunes
Book and reading-related quotes, plus classic fortunes.
Loaded lazily from fortunes.json on first use.
"""

import json
import random
from pathlib import Path

_fortunes: list[str] | None = None


def _load_fortunes() -> list[str]:
    """Load fortunes from JSON file."""
    global _fortunes
    if _fortunes is None:
        path = Path(__file__).parent / 'fortunes.json'
        with open(path, encoding='utf-8') as f:
            _fortunes = json.load(f)
    return _fortunes


def get_fortune() -> str:
    """Return a random fortune."""
    return random.choice(_load_fortunes())
