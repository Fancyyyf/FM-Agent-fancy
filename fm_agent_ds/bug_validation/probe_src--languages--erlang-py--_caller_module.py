"""Probe script for bug: src--languages--erlang-py--_caller_module

The _caller_module() function uses os.path.basename() and discards directory
components, but the specification requires forming a module identifier from
path components relative to the project root, with directory separators
replaced by '::'.

Bug ID: src--languages--erlang-py--_caller_module
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable (Python adds script dir, not CWD)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

def _expected_by_spec(path: str, proj_root: str) -> str:
    """Compute the spec-correct module identifier.

    Specification: relative path from project root, '/' → '::', final '.' → '-'.
    """
    rel = os.path.relpath(path, proj_root)
    # Replace directory separators with '::'
    parts = rel.replace(os.sep, "/").split("/")
    transformed = "::".join(parts)
    # Replace the last '.' in the filename component with '-'
    last_dot = transformed.rfind(".")
    if last_dot > 0 and transformed.rfind("::") < last_dot:
        transformed = transformed[:last_dot] + "-" + transformed[last_dot + 1 :]
    return transformed


try:
    from src.languages.erlang import _caller_module

    # ---- Test 1: path with subdirectory ----
    input_path = os.path.join(os.sep, "project", "subdir", "module.py")

    actual = _caller_module(input_path)
    expected = _expected_by_spec(input_path, os.path.join(os.sep, "project"))

    bug_reproduced = actual != expected

    if bug_reproduced:
        print(
            f"CONFIRMED — input: {input_path!r} | "
            f"actual (basename only): {actual!r} | "
            f"expected (spec: relative with :: separator): {expected!r}"
        )
    else:
        # Test 2: deep nesting
        input_path2 = os.path.join(os.sep, "root", "a", "b", "c", "file.erl")
        actual2 = _caller_module(input_path2)
        expected2 = _expected_by_spec(input_path2, os.path.join(os.sep, "root"))

        if actual2 != expected2:
            print(
                f"CONFIRMED — input: {input_path2!r} | "
                f"actual (basename only): {actual2!r} | "
                f"expected (spec: relative with :: separator): {expected2!r}"
            )
        else:
            print(
                "NOT CONFIRMED — actual matched expected for all test cases; "
                f"actual: {actual!r}, expected: {expected!r}"
            )

except Exception:
    import traceback
    traceback.print_exc()
    print("ERROR: probe script failed with an unhandled exception")
    sys.exit(1)
