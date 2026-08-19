"""Probe for phase_callee_info_names_key bug: when exact target key is absent,
the buggy code returns any key matching the pattern instead of None."""

import sys
import os

# Work from a temp directory per the self-validation guard, but we can
# still import from the project root. Add the (absolute) project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

try:
    from src.generate_batch_prompts import phase_callee_info_names_key

    # Construct a dict that has a phase-2 key but no phase-1 key.
    func = {
        "phase2_callee_info_names_by_caller": {"callerA": ["info1"]},
        "phase2_callers": ["callerA"],
    }

    # Looking for phase 1 - the exact key "phase1_callee_info_names_by_caller"
    # does NOT exist in func, so the spec requires None.
    actual = phase_callee_info_names_key(func, 1)
    expected = None  # per specification: return None when exact key is absent

    passed = actual != expected  # True means bug reproduced

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
