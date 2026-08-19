#!/usr/bin/env python3
"""Probe script for bug: _parse_spec_check_json rejects MATCH verdict with non-empty counterexample."""

import sys
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.prompts import _parse_spec_check_json

    # -----------------------------------------------------------------------
    # Test 1: MATCH verdict with non-empty counterexample (offending_statements is null)
    # Spec: does NOT list this as a ValueError case → should be accepted
    # Code: line 87-90 raises ValueError
    # -----------------------------------------------------------------------
    response1 = (
        '{"verdict": "MATCH",'
        ' "counterexample": "a concrete counterexample",'
        ' "offending_statements": null,'
        ' "reason": "all good"}'
    )

    actual1 = None
    error1 = None
    try:
        actual1 = _parse_spec_check_json(response1)
    except ValueError as e:
        error1 = str(e)

    if error1 is not None:
        print(f"CONFIRMED — bug reproduced: ValueError raised for valid MATCH verdict with non-empty counterexample")
        print(f"  Expected: should return (False, None, None, data)")
        print(f"  Actual error: {error1}")
    else:
        print(f"NOT CONFIRMED — function accepted MATCH with non-empty counterexample (spec-correct)")
        print(f"  Returned: {actual1!r}")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
