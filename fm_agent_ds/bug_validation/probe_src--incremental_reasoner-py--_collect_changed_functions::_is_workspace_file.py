"""Probe for _is_workspace_file bug: fm_agent/.. escapes the workspace but passes the prefix check.

The target function is a nested closure inside _collect_changed_functions; its exact logic is
replicated here as the smallest testable unit per the FM-Agent self-validation guard.
"""

import sys

# Exact logic from src/incremental_reasoner.py line 378-380
def _is_workspace_file(rel_path):
    norm = rel_path.replace("\\", "/")
    return norm == "fm_agent" or norm.startswith("fm_agent/")

# Expected behavior per spec:
# - True when rel_path equals "fm_agent" or starts with "fm_agent/"
# - False when path escapes the workspace (e.g. via "..")

test_cases = [
    # (rel_path, expected_per_spec, description)
    ("fm_agent", True, "exact match"),
    ("fm_agent/some_file.py", True, "descendant inside workspace"),
    ("fm_agent/nested/deep/file.c", True, "deeply nested descendant"),
    ("fm_agent\\subdir\\file.rs", True, "Windows backslash normalization"),
    ("src/main.py", False, "outside workspace entirely"),
    ("", False, "empty path"),
    ("fm", False, "partial prefix match, not fm_agent"),
    ("fm_agent/..", False, ".. escapes the workspace directory"),
    ("fm_agent/../escape.py", False, ".. escape with trailing file"),
    ("fm_agent/../../outside", False, "double .. escape"),
    ("fm_agent/subdir/../../../root.txt", False, "nested then .. escape"),
    ("fm_agent\\..\\escape.rs", False, "Windows backslash .. escape"),
]

all_passed = True
results = []

for rel_path, expected, desc in test_cases:
    try:
        actual = _is_workspace_file(rel_path)
        passed = actual == expected
        status = "PASS" if passed else "FAIL"
        results.append((status, rel_path, expected, actual, desc))
        if not passed:
            all_passed = False
    except Exception as e:
        results.append(("ERROR", rel_path, expected, str(e), desc))
        all_passed = False

# Print results
for status, rel_path, expected, actual, desc in results:
    print(f"[{status}] rel_path={rel_path!r}  expected={expected}  actual={actual}  ({desc})")

# Overall verdict: the bug is CONFIRMED if any test case that should be False returns True.
buggy_cases = [r for r in results if r[0] == "FAIL"]

if buggy_cases:
    print(f"\nCONFIRMED — {len(buggy_cases)} test case(s) expose the bug:")
    for status, rel_path, expected, actual, desc in buggy_cases:
        print(f"  rel_path={rel_path!r}: expected {expected}, got {actual} ({desc})")
else:
    print("\nNOT CONFIRMED — all test cases matched expected behavior")
