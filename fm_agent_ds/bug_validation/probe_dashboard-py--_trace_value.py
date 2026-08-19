import sys
import os

# Resolve the repo root from the probe's location
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from dashboard import _trace_value
except Exception as e:
    print(f"ERROR: Failed to import dashboard._trace_value: {e}")
    sys.exit(1)

# Bug: code uses `if candidate in d` (key existence) but spec requires
# "first field that has a truthy value". A falsy value in an existing key
# causes code to return that falsy value instead of skipping it.
#
# Spec expects: skip falsy value 0 for key "status" → return None.
# Code does: key "status" exists in d → return d["status"] = 0.

try:
    actual = _trace_value({"status": 0}, "status")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if actual is not None:
    # Bug confirmed: returned falsy 0 instead of skipping to None
    print(f"CONFIRMED — actual: {actual!r} | expected (spec-correct): None")
else:
    print(f"NOT CONFIRMED — actual matched spec-expected: None")
