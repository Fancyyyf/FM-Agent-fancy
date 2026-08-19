import sys
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

try:
    from dashboard import _llm_code_for_event
except Exception as e:
    print(f"ERROR: failed to import dashboard: {e}")
    sys.exit(1)

actual = None
passed = False

try:
    # The spec requires any general error status (including 'ERROR' in any case)
    # to return 'ERR'. The code only checks for exact lowercase 'error',
    # so 'ERROR' falls through and returns 'ERROR' unchanged.
    actual = _llm_code_for_event("ERROR")
    expected = "ERR"
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
