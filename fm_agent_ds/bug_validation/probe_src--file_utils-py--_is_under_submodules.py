"""Probe for bug: _is_under_submodules does not resolve '..' in paths.

The function uses a simple string prefix check (startswith) without resolving
parent-directory references, so `sub/../file.txt` incorrectly matches submodule `sub`.
"""

import sys
import os

# Ensure repo root is on sys.path so we can import via the package entry point
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.file_utils import _is_under_submodules


def main():
    """Run the bug-confirmation tests and print CONFIRMED or NOT CONFIRMED."""
    test_cases = []

    # Test 1: submodules=None → should return True (baseline, no bug here)
    try:
        r = _is_under_submodules("anything/at/all", None)
        test_cases.append(("submodules=None → True", r, True, "baseline None check"))
    except Exception as e:
        print(f"ERROR: test 1 failed with exception: {e}")
        sys.exit(1)

    # Test 2: file properly inside submodule → should return True (baseline)
    try:
        r = _is_under_submodules("sub/real_file.txt", ["sub"])
        test_cases.append(("'sub/real_file.txt' under ['sub'] → True", r, True, "valid in-submodule path"))
    except Exception as e:
        print(f"ERROR: test 2 failed with exception: {e}")
        sys.exit(1)

    # Test 3: THE BUG — path with .. that resolves outside submodule → should be False
    try:
        r = _is_under_submodules("sub/../file.txt", ["sub"])
        test_cases.append(("'sub/../file.txt' under ['sub'] → False", r, False, "SPEC: False (resolves to 'file.txt', not under 'sub')"))
    except Exception as e:
        print(f"ERROR: test 3 failed with exception: {e}")
        sys.exit(1)

    # Test 4: file NOT in submodule → should return False (baseline)
    try:
        r = _is_under_submodules("other/thing.txt", ["sub"])
        test_cases.append(("'other/thing.txt' under ['sub'] → False", r, False, "file not under submodule"))
    except Exception as e:
        print(f"ERROR: test 4 failed with exception: {e}")
        sys.exit(1)

    # Evaluate: bug is CONFIRMED if Test 3 returned True (wrong) while Test 4 returned False (correct)
    _, r_bug, expected_bug, _ = test_cases[2]
    bug_reproduced = r_bug != expected_bug

    if bug_reproduced:
        print(f"CONFIRMED — bug reproduced: _is_under_submodules does not resolve '..'")
        for desc, actual, expected, note in test_cases:
            match = "MATCH" if actual == expected else "BUG"
            print(f"  [{match}] {desc}: actual={actual!r}, expected={expected!r} | {note}")
    else:
        print(f"NOT CONFIRMED — all results matched expected:")
        for desc, actual, expected, note in test_cases:
            print(f"  [PASS] {desc}: {actual!r}")


if __name__ == "__main__":
    main()
