"""Probe script for bug src--languages--codegraph-py--_fqn_for.

The bug: _fqn_for uses `last_dot > 0` to guard dot replacement, which
excludes basenames where the dot is the first character (e.g. '.hidden').
The spec requires replacing the last '.' with '-' regardless of its position.
"""
import sys
import os

# Ensure the repo root is on sys.path so the package entry point resolves.
# probe is at fm_agent/bug_validation/probe_...py → 3 levels up = repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.codegraph import _fqn_for

    # Trigger condition: file_path='dir/.hidden', name='func'
    actual = _fqn_for("dir/.hidden", "func")

    # Spec-correct: last '.' in basename '.hidden' → '-hidden', yielding 'dir::-hidden::func'
    expected = "dir::-hidden::func"

    # The bug exists if actual != expected
    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
