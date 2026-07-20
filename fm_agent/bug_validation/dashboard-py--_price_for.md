# Bug Report: _price_for

**Source file:** `dashboard.py`
**Extracted function:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/_price_for.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict whose keys are per-token pricing component names and
    whose values are positive float per-token costs in USD for the model
    identified by model, or None when no pricing data is available
  - A model identifier that contains a "/" character (provider-prefixed
    form such as "provider/model") is recognized under both its full
    provider-prefixed form and its bare form (the substring following the
    first "/"); a match in either form is sufficient
  - Returns None when model is falsy, or when the model identifier has no
    matching pricing data in either its full or bare form

---

### Actual Behavior

The function returns None if the input model is falsy (e.g., None, empty string). Otherwise, if model is a truthy string and exists as a key in the global _MODEL_COST dictionary, the function returns the corresponding price. If model is not in _MODEL_COST but contains a '/', the substring after the first '/' is extracted; if this substring exists as a key in _MODEL_COST, that price is returned. In all other cases, the function returns None. No modifications are made to the input or the _MODEL_COST mapping. Formally, for return value r: r = None  (bool(model))  (bool(model)  (model  _MODEL_COST)  (('/'  model)  (model.split('/', 1)[1]  _MODEL_COST))). r = _MODEL_COST[model]  bool(model)  model  _MODEL_COST. r = _MODEL_COST[model.split('/', 1)[1]]  bool(model)  model  _MODEL_COST  '/'  model  model.split('/', 1)[1]  _MODEL_COST.

---

## Code Evidence

Line 6: `return _MODEL_COST[key]` and Line 11: `return _MODEL_COST[bare]`

---

## Trigger Condition

The specification requires the function to return either a dict whose keys are per-token pricing component names and whose values are positive floats, or None. The code does not validate the type of the value retrieved from _MODEL_COST; it returns whatever is stored. If _MODEL_COST holds a non-dict (e.g., a float 0.03) for a valid model, the code returns that value, which violates the specification's dict requirement.

---

## How to trigger the bug

When `_MODEL_COST` contains a non-dict value for a model key (e.g., a bare float `0.03` instead of a structured dict with pricing component keys), `_price_for` returns that non-dict value directly. This violates the specification because the function is documented to return either a `dict` or `None` — a bare float is neither.

### Inputs

| Parameter | Value |
|-----------|-------|
| `model` | `"__bug_validator_test_model__"` (synthetic key with non-dict value) |

### Expected (spec-correct) Output

`None` (because the stored value is not a properly structured dict, so pricing data should be treated as unavailable)

### Actual (buggy) Output

`0.03` (a bare `float` — not a dict, not None)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard

# Inject a non-dict value into the pricing lookup
dashboard._MODEL_COST["__bug_validator_test_model__"] = 0.03

# Call the pricing function — returns a float, violating the spec
result = dashboard._price_for("__bug_validator_test_model__")
# actual (buggy) output: 0.03 (type: float)
# expected (correct) output: None (or a proper dict)
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: 0.03 (type=float) | expected: None (or dict)
```
