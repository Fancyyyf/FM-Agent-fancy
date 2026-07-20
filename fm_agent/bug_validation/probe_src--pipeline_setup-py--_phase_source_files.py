"""Probe for _phase_source_files: test that a valid JSON array (not object)
causes an AttributeError instead of returning {} per the specification."""
import sys
import os
import json
import tempfile

# Ensure repo root is on path so 'config' and 'src' resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(repo_root)
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _phase_source_files
except Exception as e:
    print(f"ERROR: import {e}")
    sys.exit(1)

# ---- Test: valid JSON array instead of object -------------------------------
# The spec says: "When phases_json cannot be read (file missing, unreadable)
# or contains invalid JSON, returns an empty dict."
# However, a bare JSON array like '[]' is VALID JSON that json.load() will
# parse into a Python list, NOT a dict. The code then calls data.get("phases", [])
# which crashes with AttributeError because lists have no .get() method.

tmp_path = os.path.join(repo_root, "fm_agent", "bug_validation", "_tmp_probe_phases.json")

try:
    with open(tmp_path, "w") as f:
        f.write("[]")

    actual = _phase_source_files(tmp_path)

    # If we got here without an AttributeError, the function handled it.
    expected = {}  # spec says: invalid/unreadable → empty dict
    bug_present = not isinstance(actual, dict) or actual != expected

    if bug_present:
        print(f"CONFIRMED — valid JSON array returned non-empty: {actual!r} (expected: {{}})")
    else:
        print(f"NOT CONFIRMED — empty dict returned for JSON array as spec requires: {actual!r}")

except AttributeError as e:
    # The bug: data.get() failed because data is a list, not a dict.
    print(f"CONFIRMED — AttributeError on JSON array (expected empty dict per spec): {e}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
