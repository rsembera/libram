#!/usr/bin/env python3
"""
Test script for the pages-per-month proportional attribution logic.
Verifies distribute_pages_across_months() splits a book's pages across the
calendar months its reading spanned, proportional to days in each month.
"""

import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import distribute_pages_across_months


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def test_distribution():
    """Run the attribution cases and report PASS/FAIL."""
    print("=== Pages Per Month Attribution Test ===\n")
    checks = []

    # 1. Book entirely within one month -> all pages in that month
    r = distribute_pages_across_months(date(2026, 6, 5), date(2026, 6, 20), 300)
    ok = r == {(2026, 6): 300.0}
    checks.append(("Single month, all pages in June", ok))

    # 2. Clean 25 / 75 split across two months
    #    June 27-30 = 4 days, July 1-12 = 12 days, total 16 days -> 25% / 75%
    r = distribute_pages_across_months(date(2026, 6, 27), date(2026, 7, 12), 400)
    ok = approx(r[(2026, 6)], 100.0) and approx(r[(2026, 7)], 300.0)
    checks.append(("25/75 split: June=100, July=300", ok))

    # 3. Three-month span produces three buckets that sum to the page total
    r = distribute_pages_across_months(date(2026, 5, 20), date(2026, 7, 10), 510)
    ok = set(r.keys()) == {(2026, 5), (2026, 6), (2026, 7)} and approx(sum(r.values()), 510.0)
    checks.append(("Three-month span sums to 510", ok))

    # 4. Single-day read -> one bucket, all pages
    r = distribute_pages_across_months(date(2026, 6, 15), date(2026, 6, 15), 88)
    ok = r == {(2026, 6): 88.0}
    checks.append(("Single-day read, all 88 pages in June", ok))

    # 5. Year boundary span (Dec -> Jan) buckets correctly and sums
    r = distribute_pages_across_months(date(2025, 12, 30), date(2026, 1, 2), 400)
    #    Dec 30-31 = 2 days, Jan 1-2 = 2 days -> 200 / 200
    ok = (set(r.keys()) == {(2025, 12), (2026, 1)}
          and approx(r[(2025, 12)], 200.0) and approx(r[(2026, 1)], 200.0))
    checks.append(("Dec->Jan boundary: 200 each", ok))

    # 6. Defensive: finished before begun collapses to begun's month
    r = distribute_pages_across_months(date(2026, 6, 10), date(2026, 6, 1), 120)
    ok = r == {(2026, 6): 120.0}
    checks.append(("finished < begun guard", ok))

    # 7. Sum invariant: attributed pages always equal the input total
    r = distribute_pages_across_months(date(2026, 2, 14), date(2026, 6, 3), 777)
    ok = approx(sum(r.values()), 777.0)
    checks.append(("Sum invariant over long span", ok))

    print("=== Verification ===")
    for label, ok in checks:
        print(f"  {label}: {'PASS' if ok else 'FAIL'}")

    all_passed = all(ok for _, ok in checks)
    print(f"\n{'='*40}")
    print(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print(f"{'='*40}")
    return all_passed


if __name__ == '__main__':
    sys.exit(0 if test_distribution() else 1)
