"""Probe for bug: _nonempty_string treats whitespace-only strings as empty,
violating the _parse_spec_check_json spec for MATCH verdict."""

import json
import sys

# Add repo root to path so src.prompts import resolves
sys.path.insert(0, ".")

try:
    from src.prompts import _parse_spec_check_json
except ImportError as e:
    print(f"ERROR: Could not import _parse_spec_check_json: {e}")
    sys.exit(1)

# Build a MATCH-verdict JSON where counterexample is a whitespace-only string.
# Per the spec, any non-empty string (length > 0) should trigger ValueError.
# The code's _nonempty_string uses bool(value.strip()), which treats
# whitespace-only as empty and does NOT raise.
match_with_whitespace_counterexample = json.dumps({
    "verdict": "MATCH",
    "counterexample": "   ",
    "offending_statements": "   ",
    "reason": "The code behaves correctly.",
})

try:
    result = _parse_spec_check_json(match_with_whitespace_counterexample)
    # No ValueError → bug reproduced.
    actual = result
    expected = "ValueError"
    print(f"CONFIRMED — _nonempty_string treats whitespace-only as empty, "
          f"but spec requires ValueError for any non-empty string. "
          f"Actual: returned tuple {result[:3]!r} (no error) | Expected: {expected!r}")
except ValueError:
    # ValueError raised → spec-correct behavior.
    print("NOT CONFIRMED — ValueError correctly raised for whitespace-only counterexample/offending_statements")
except Exception as e:
    print(f"ERROR: Unexpected exception: {e}")
    sys.exit(1)
