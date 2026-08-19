import sys
import os

# When run from repo root via `python3 fm_agent/bug_validation/probe_<id>.py`,
# os.getcwd() is the repo root. Add it to sys.path.
_repo_root = os.getcwd()
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.pipeline_setup import _collect_changed_phases

    # The bug: _collect_changed_phases adds keys from the "augmented" dict
    # without verifying they are integers. The spec_claim says the returned
    # set contains "unique integer phase numbers".
    #
    # Input with a non-integer key "invalid" as a string:
    ensure_changes = {"augmented": {"invalid": "value", 1: "valid"}}

    actual = _collect_changed_phases(ensure_changes)

    # Spec-expected: only integer keys → {1}
    # Buggy actual:   includes the string key "invalid" → {"invalid", 1}
    expected = {1}

    if actual != expected:
        print(
            f"CONFIRMED — actual: {sorted(actual, key=str)!r} "
            f"| expected: {sorted(expected)!r}"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    import traceback

    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
