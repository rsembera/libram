"""
Libram Astrology Module
Sun and Moon sign calculations.
"""

from __future__ import annotations

import math
import ephem
from datetime import datetime, timezone
from typing import Optional


# Zodiac signs with symbols (using text variant selector U+FE0E)
ZODIAC: list[tuple[str, str]] = [
    ('Aries', '♈︎'),
    ('Taurus', '♉︎'),
    ('Gemini', '♊︎'),
    ('Cancer', '♋︎'),
    ('Leo', '♌︎'),
    ('Virgo', '♍︎'),
    ('Libra', '♎︎'),
    ('Scorpio', '♏︎'),
    ('Sagittarius', '♐︎'),
    ('Capricorn', '♑︎'),
    ('Aquarius', '♒︎'),
    ('Pisces', '♓︎'),
]


def _ecliptic_longitude_to_sign(longitude_rad: float) -> tuple[str, str]:
    """Convert ecliptic longitude (radians) to zodiac sign."""
    degrees = math.degrees(longitude_rad) % 360
    sign_index = int(degrees / 30)
    return ZODIAC[sign_index]


def get_sun_sign(dt: Optional[datetime] = None) -> tuple[str, str]:
    """Get the current sun sign."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    sun = ephem.Sun(dt)
    name, symbol = _ecliptic_longitude_to_sign(ephem.Ecliptic(sun).lon)
    return name, symbol


def get_moon_sign(dt: Optional[datetime] = None) -> tuple[str, str]:
    """Get the current moon sign."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    moon = ephem.Moon(dt)
    name, symbol = _ecliptic_longitude_to_sign(ephem.Ecliptic(moon).lon)
    return name, symbol


def get_astrology_line(dt: Optional[datetime] = None) -> dict[str, str]:
    """Get formatted astrology line for display."""
    sun_name, sun_symbol = get_sun_sign(dt)
    moon_name, moon_symbol = get_moon_sign(dt)
    
    return {
        'sun': sun_symbol,
        'moon': moon_symbol
    }


if __name__ == '__main__':
    # Test
    print(get_astrology_line())
