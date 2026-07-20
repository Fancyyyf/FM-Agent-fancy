"""Probe script for bug dashboard-py--_cost_from_usage.

The function _cost_from_usage uses `usage.get(k, 0) or 0` to retrieve token counts.
When usage values are truthy non-numeric strings (e.g. "150"), Python raises
TypeError when multiplying by a float price: "can't multiply sequence by non-int
of type 'float'". The spec claims the function always returns a non-negative float.
"""

import os
import sys

# Ensure the repo root is on the import path so `import dashboard` works
# when the script is invoked as: python3 fm_agent/bug_validation/probe_...py
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    import dashboard
except ImportError as e:
    print(f'ERROR: could not import dashboard: {e}')
    sys.exit(1)

# Use a known model that has pricing data to ensure _price_for returns a dict.
# gpt-4 is available via litellm and has known pricing.
MODEL = "gpt-4"

# Verify _price_for returns usable data
p = dashboard._price_for(MODEL)
if not p:
    print(f'ERROR: _price_for("{MODEL}") returned falsy — cannot test')
    sys.exit(1)

# Trigger condition: usage dict with string token values instead of ints.
# The code does `usage.get("input_tokens", 0) or 0`, which keeps "150" (truthy),
# then tries `"150" * p.get("input_cost_per_token")` → TypeError.
buggy_usage = {"input_tokens": "150", "output_tokens": "50"}

passed = False
actual = None
error_msg = None

try:
    actual = dashboard._cost_from_usage(MODEL, buggy_usage)
    # If we reach here, the function returned a value instead of raising TypeError.
    # The spec requires a non-negative float, so check if the result is valid.
    expected = 150 * (p.get("input_cost_per_token") or 0) + 50 * (p.get("output_cost_per_token") or 0)
    passed = isinstance(actual, float) and actual != expected
except TypeError as e:
    # Bug reproduced: the function raised TypeError instead of returning a float.
    passed = True
    error_msg = str(e)
except Exception as e:
    error_msg = f'{type(e).__name__}: {e}'

if passed and error_msg:
    print(f'CONFIRMED — TypeError raised: {error_msg} | expected: float, got: exception')
elif passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: valid float')
elif error_msg:
    print(f'ERROR: {error_msg}')
else:
    print(f'NOT CONFIRMED — actual matched expected behavior: {actual!r}')
