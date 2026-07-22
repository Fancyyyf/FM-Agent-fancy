#!/usr/bin/env python3
"""Probe script for bug: src--languages--codegraph-py--_extraction_ident

Tests whether _extraction_ident produces empty components when
_bare_function_name returns "" for whitespace-only qualifier parts,
violating the spec that the returned string must be composed of
non-empty components joined by "::".
"""
import sys
import os
import tempfile

# ── Use a fresh temp directory as probe workspace ──
os.chdir(tempfile.mkdtemp())

# Ensure the repo root is on sys.path so the public module can be imported.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Import via the package entry point
from src.languages.codegraph import _extraction_ident


def check(name, qualified_name):
    """Call _extraction_ident and check for empty components in result."""
    actual = _extraction_ident(name, qualified_name)
    components = actual.split("::")
    has_empty = any(c == "" for c in components)
    return actual, has_empty, components


def main():
    # The bug: _qualified_parts returns ["foo", " ", "func"] because
    # _qualified_parts' filter "if p" doesn't catch whitespace-only
    # strings. _bare_function_name(" ") returns "" and canonicalize("")
    # returns "", so "::".join(["foo", "", "func"]) = "foo::::func",
    # which has an empty component — violating the spec.

    bugs_found = []
    no_bugs = []

    test_cases = [
        ("func", "foo:: ::func",  "whitespace-only middle qualifier"),
        ("func", " ::func",        "leading space before ::name"),
        ("bar",  " ::A::bar",      "leading space, nested qualifier"),
        ("baz",  "X:: ::\tbaz",    "space+tab qualifier"),
    ]

    for name, qname, desc in test_cases:
        actual, has_empty, components = check(name, qname)
        if has_empty:
            bugs_found.append((name, qname, desc, actual, components))
        else:
            no_bugs.append((name, qname, desc, actual))

    if bugs_found:
        print("CONFIRMED — Empty components found in _extraction_ident output")
        for name, qname, desc, actual, components in bugs_found:
            print(f"  [{desc}] name={name!r}, qualified_name={qname!r}")
            print(f"    actual:   {actual!r}")
            print(f"    split by '::': {components!r} (contains empty!)")
    else:
        print("NOT CONFIRMED — No empty components found in any test case")
        for name, qname, desc, actual in no_bugs:
            print(f"  [{desc}] actual={actual!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
