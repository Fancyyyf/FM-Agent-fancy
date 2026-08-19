import sys
import os
from pathlib import Path

# The probe runs from the repo root; ensure the repo root is on the path
# so that 'import dashboard' finds dashboard.py.
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    import dashboard
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

actual = None
expected = {1: "a"}
passed = False
error_msg = None

try:
    actual = dashboard._strip_star({1: "a"})
    # If we get here without exception, the function returned successfully.
    # Check: did the non-string key survive unchanged as spec requires?
    passed = actual != expected
except AttributeError as e:
    # Bug confirmed: k.startswith("*") raised AttributeError on integer key
    error_msg = str(e)
    passed = True   # Bug reproduced: exception instead of returning unchanged
except Exception as e:
    error_msg = str(e)
    passed = False  # Unexpected error type

if passed:
    if error_msg:
        print(f"CONFIRMED — AttributeError raised on non-string key: {error_msg!r} | expected: {expected!r}")
    else:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
