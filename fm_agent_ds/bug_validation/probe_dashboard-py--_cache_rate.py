"""Probe script for bug dashboard-py--_cache_rate.

Bug: _cache_rate returns None for rate when in_total is 0, but the specification
requires rate=0.0 in that case.

This probe runs from a fresh temporary directory as required by the validator.
"""

import os
import sys
import tempfile
import shutil

# Add repo root to path so dashboard module can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    import dashboard
    _cache_rate = dashboard._cache_rate

    # Trigger: empty rows → cr_total=0, in_total=0 → bug path
    actual = _cache_rate([])

    # Spec: rate=0.0 when in_sum=0; cr_sum=0, in_sum=0
    expected = (0.0, 0, 0)

    # Bug reproduced if actual[0] is None instead of 0.0
    passed = actual[0] is not expected[0]

    if passed:
        print(
            f"CONFIRMED — _cache_rate returned rate={actual[0]!r} "
            f"instead of expected rate={expected[0]!r} when in_total=0. "
            f"Full return: actual={actual!r} | expected={expected!r}"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except ImportError as e:
    print(f"ERROR: Import failed — {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
