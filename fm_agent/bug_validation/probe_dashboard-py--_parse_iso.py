"""Probe script for dashboard-py--_parse_iso: verify timezone-naive datetime returned for valid ISO 8601 without timezone."""
import sys
import os

# Add repo root to path so `import dashboard` resolves (project is not a package)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard

    ts = "2023-10-01T12:00:00"
    actual = dashboard._parse_iso(ts)

    # Spec requires timezone-aware datetime on successful parse.
    # Bug: actual has no tzinfo (naive datetime) for inputs without explicit timezone.
    passed = actual is not None and actual.tzinfo is None

    if passed:
        print(f"CONFIRMED — _parse_iso({ts!r}) returned naive datetime {actual!r} (tzinfo=None), spec requires timezone-aware")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
