"""Probe for _collect_changed_phases: test that non-integer phase numbers are
erroneously included when only None is checked."""
import sys
import os

# Ensure repo root is on path so 'config' and 'src' resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(repo_root)
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _collect_changed_phases
except Exception as e:
    print(f"ERROR: import {e}")
    sys.exit(1)

# ---- Test 1: non-integer string as augmented key --------------------------
# The spec says only non-None integers should appear.  A string should be
# excluded, but the code only guards against None.
try:
    ensure_changes = {"augmented": {5: True, "abc": True, None: True}}
    result = _collect_changed_phases(ensure_changes)

    # Spec requires result to contain only non-None integers.
    non_ints_in_result = [v for v in result if not isinstance(v, int)]
    bug_present = len(non_ints_in_result) > 0

    display_actual = sorted(result, key=str)

    if bug_present:
        print(f"CONFIRMED — augmented-keys: included non-integers {non_ints_in_result!r} "
              f"| full result={display_actual!r}")
    else:
        print(f"NOT CONFIRMED — augmented-keys: result contains only integers: {display_actual!r}")
except Exception as e:
    print(f"ERROR: test1 {e}")
    sys.exit(1)

# ---- Test 2: non-integer float as modified_modules phase ------------------
try:
    change_sets = ({"modified_modules": [
        {"phase": 10},
        {"phase": 3.14},   # float — not an integer, should be excluded per spec
        {"phase": None},
    ]},)
    result2 = _collect_changed_phases({}, *change_sets)

    non_ints2 = [v for v in result2 if not isinstance(v, int)]
    bug_present2 = len(non_ints2) > 0

    display_actual2 = sorted(result2, key=str)

    if bug_present2:
        print(f"CONFIRMED — modified_modules: included non-integers {non_ints2!r} "
              f"| full result={display_actual2!r}")
    else:
        print(f"NOT CONFIRMED — modified_modules: result contains only integers: {display_actual2!r}")
except Exception as e:
    print(f"ERROR: test2 {e}")
    sys.exit(1)
