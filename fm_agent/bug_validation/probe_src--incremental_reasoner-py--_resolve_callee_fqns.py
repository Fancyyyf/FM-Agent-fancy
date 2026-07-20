import sys
import os

# Ensure the repo root is on sys.path so 'src' is importable as a package.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _resolve_callee_fqns
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Trigger condition: callee_names contains strings with surrounding whitespace,
# and the callee FQN's stem also contains whitespace. The spec requires a
# case-insensitive match against the original strings in callee_names (without
# stripping). The code strips whitespace, so the match fails.

caller_fqn = "module::function"
callee_names = ["  foo  "]
callees_map = {
    "module::function": ["path::to::  foo  "]
}

try:
    actual = _resolve_callee_fqns(caller_fqn, callee_names, callees_map)
    # Per the spec, "  foo  " should case-insensitively match "  foo  " → the FQN should be included.
    expected = {"path::to::  foo  "}
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
