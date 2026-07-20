# Bug Report: _cost_from_usage

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/_cost_from_usage.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a non-negative float representing the total cost in USD of
    the token consumption recorded in usage, priced according to the
    per-token rates of the model's known pricing tier
  - Four token categories are recognized: input tokens, output tokens,
    cache-read tokens, and cache-creation tokens; each is priced at a
    distinct per-token rate determined independently by the model's
    pricing tier
  - A token category not present in usage, or present with a falsy
    value, contributes zero to the total
  - A pricing component not present in the model's tier contributes
    zero to the total
  - Returns 0.0 when model is None, usage is falsy, or no pricing tier
    is associated with model

---

### Actual Behavior

The function returns a non-negative float value `cost` representing the total cost in USD for the given usage, computed from per-token prices obtained via `_price_for(model)`. If `_price_for(model)` returns a falsy value (e.g., `None`) or if `usage` is falsy (e.g., `None`), `cost` is exactly `0.0`. Otherwise, let `p = _price_for(model)` be a dictionary mapping price component names to positive floats. For each token type `k` in {"input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"}, let `tokens_k = (usage.get(k, 0) or 0)` (i.e., the token count if present and truthy, else 0). The corresponding price `price_k = (p.get(price_key) or 0)` where the price key for each token type is: "input_cost_per_token" for input_tokens, "output_cost_per_token" for output_tokens, "cache_read_input_token_cost" for cache_read_input_tokens, and "cache_creation_input_token_cost" for cache_creation_input_tokens. Then `cost = _k (tokens_k * price_k)`. The function has no side effects: `model` and `usage` are not modified, and no exceptions are raised. Formally: ( cost : ) (cost >= 0)  ( (_price_for(model) is falsy  usage is falsy)  cost = 0.0 )  ( (_price_for(model) is truthy  usage is truthy)   p = _price_for(model) : (cost = (usage.get("input_tokens",0) or 0) * (p.get("input_cost_per_token") or 0) + (usage.get("output_tokens",0) or 0) * (p.get("output_cost_per_token") or 0) + (usage.get("cache_read_input_tokens",0) or 0) * (p.get("cache_read_input_token_cost") or 0) + (usage.get("cache_creation_input_tokens",0) or 0) * (p.get("cache_creation_input_token_cost") or 0) ) )

---

## Code Evidence

Line 6, Line 7, Line 8, Line 9, Line 11, Line 12, Line 13, Line 14

---

## Trigger Condition

The code retrieves token counts using `usage.get(k, 0) or 0`, which retains any truthy nonnumeric value (e.g., a string). Later it multiplies this value by a float price, e.g., `'150' * 0.01`. Python raises a TypeError ('can't multiply sequence by non-int of type float'), so the function fails to return a float, violating the specification's requirement to always return a nonnegative float (or 0.0).

---

## How to trigger the bug

When `usage` dict values are truthy non-numeric strings (e.g., `"150"`), the expression `usage.get(k, 0) or 0` retains the string. Multiplying the string by a float price raises `TypeError: can't multiply sequence by non-int of type 'float'`, crashing the caller instead of returning a float.

### Inputs

| Parameter | Value |
|-----------|-------|
| `model` | `"gpt-4"` (a model with known pricing in litellm) |
| `usage` | `{"input_tokens": "150", "output_tokens": "50"}` |

### Expected (spec-correct) Output

`0.0075` (float: `150 * 0.00003 + 50 * 0.00006`)

### Actual (buggy) Output

`TypeError: can't multiply sequence by non-int of type 'float'` — the function raises an exception instead of returning a float.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard
try:
    result = dashboard._cost_from_usage("gpt-4", {"input_tokens": "150", "output_tokens": "50"})
    print(f"result: {result}")
except TypeError as e:
    print(f"TypeError: {e}")  # actual (buggy) output
# expected (correct) output: 0.0075
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — TypeError raised: can't multiply sequence by non-int of type 'float' | expected: float, got: exception
```
