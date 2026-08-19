"""Probe for _is_path_function_label bug: PurePosixPath strips trailing slash,
making the final path component non-empty when the spec requires it to be empty."""

import sys
import os

# Ensure repo root is on the import path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.call_graph_edges import normalize_fqn_label

    label = "a/b.c/::func"

    # Spec: the final POSIX-path component after the last '/' is '' (empty),
    # which does NOT contain '.', so _is_path_function_label should return False
    # and normalize_fqn_label should return the label unchanged.
    expected = "a/b.c/::func"

    # Actual: PurePosixPath('a/b.c/').name returns 'b.c', which contains '.',
    # so the function incorrectly treats it as a path-function label and normalizes it.
    actual = normalize_fqn_label(label)

    # Bug reproduced if actual != expected
    bug_confirmed = actual != expected

    if bug_confirmed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
