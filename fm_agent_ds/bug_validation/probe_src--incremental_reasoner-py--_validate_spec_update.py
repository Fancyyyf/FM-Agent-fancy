"""Probe script for bug src--incremental_reasoner-py--_validate_spec_update.

Spec claim: _validate_spec_update(data) returns None when data is not a dict.
Actual behavior: _validate_spec_update(data) raises ValueError('spec-update JSON must be an object').
"""

import sys
import os

# Add the repo root to the path so we can import src.incremental_reasoner
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _validate_spec_update

    # Test with a non-dict input (a string) -- spec says return None, code raises ValueError
    passed = False
    try:
        result = _validate_spec_update("not a dict")
        # If we get here, the function returned something (not raised). Could be None or something else.
        # spec says None, so pass if it returned something other than None (which means the spec is wrong), 
        # but we're testing the bug: code raises ValueError instead of returning None.
        # Since a non-None result is also wrong, we check:
        # The bug specifically says: spec says return None, code raises ValueError.
        # But we didn't get ValueError, so the bug might NOT be confirmed in this case.
        # WARNING: This would mean the code was changed.
        print(f"NOT CONFIRMED — no ValueError raised, returned: {result!r}")
        sys.exit(0)
    except ValueError as e:
        # Bug reproduced: code raised ValueError when spec says it should return None
        expected_return = None
        actual_behavior = f"ValueError: {e}"
        print(f"CONFIRMED — actual: {actual_behavior!r} | expected: {expected_return!r}")
        sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
