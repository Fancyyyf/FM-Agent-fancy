"""Probe script for bug dashboard-py--_price_for.

Spec claim: _price_for() must return a dict (with per-token pricing component
names -> positive float costs) or None. The code returns whatever is stored in
_MODEL_COST without validating the type. If _MODEL_COST holds a non-dict
(e.g., a bare float), the function returns that non-dict value, violating the spec.
"""

import sys
import os

# Ensure we can import dashboard.py from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    import dashboard

    # Inject a non-dict value into _MODEL_COST for a synthetic test model.
    # The spec forbids returning a non-dict, so the function should not return
    # this bare float.
    test_model = "__bug_validator_test_model__"
    dashboard._MODEL_COST[test_model] = 0.03  # bare float, not a dict

    actual = dashboard._price_for(test_model)
    # Expected: the spec says the function must return a dict or None.
    # A bare float 0.03 is neither. Per spec, when properly structured pricing
    # data is unavailable, None should be returned.
    expected = None

    # Bug is CONFIRMED if actual is not a dict (i.e., the function returned
    # the bare float instead of None or a proper dict)
    passed = not isinstance(actual, dict) and actual is not None

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} (type={type(actual).__name__}) | expected: {expected!r} (or dict)")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
