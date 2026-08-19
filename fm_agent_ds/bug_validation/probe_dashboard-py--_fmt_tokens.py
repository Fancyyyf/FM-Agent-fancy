"""Probe script for bug dashboard-py--_fmt_tokens.

Bug: _fmt_tokens formats M-range values with two decimal places (:.2f),
but the specification requires at most one decimal place.
"""

import os
import sys

# Add repo root to path so dashboard module can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    import dashboard
    actual = dashboard._fmt_tokens(1_000_000)

    # Spec says "at most one decimal place" for M values.
    # The code uses .2f → always 2 decimal places → bug.
    if actual.endswith("M"):
        body = actual[:-1]
        decimal_places = len(body.split(".")[1]) if "." in body else 0
        passed = decimal_places > 1
    else:
        decimal_places = 0
        passed = False

    if passed:
        expected_example = f"{1_000_000/1_000_000:.1f}M"
        print(
            f"CONFIRMED — _fmt_tokens(1_000_000) returned {actual!r} "
            f"({decimal_places} decimal places), "
            f"but spec allows at most 1 decimal place (e.g. {expected_example!r})"
        )
    else:
        print(f"NOT CONFIRMED — actual: {actual!r}")

except ImportError as e:
    print(f"ERROR: Import failed — {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
