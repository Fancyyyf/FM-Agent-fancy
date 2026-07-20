# Bug Report: _order_key

**Source file:** `src/incremental_reasoner-py/_order_key.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a two-element tuple (position, fqn) suitable as a sort key for top-down topological ordering
- When fqn is a key in order_index, position equals the integer value associated with fqn in order_index
- When fqn is not a key in order_index, position equals the number of entries in order_index
- For any two FQNs a, b both present in order_index: a sorts before b iff order_index[a] < order_index[b]
- Any FQN not present in order_index sorts after all FQNs that are present in order_index

---

### Actual Behavior

The function _order_key returns a tuple (index, fqn) where index equals order_index[fqn] if fqn is a key in order_index, otherwise index equals len(order_index). The dictionary order_index is not modified, and no exceptions are raised. Formally: result = (order_index.get(fqn, len(order_index)), fqn) and for all k in order_index, order_index[k] is unchanged and the set of keys is unchanged.

---

## Code Evidence

Line 2:     return (order_index.get(fqn, len(order_index)), fqn)

---

## Trigger Condition

The default for absent keys is len(order_index), which can be smaller than the integer value stored for some present key. The specification requires that absent entries sort after all present entries, but if order_index contains a value >= len(order_index), the tuple ordering makes the absent entry appear first, breaking the guarantee.

---

## How to trigger the bug

The _order_key function has a genuine logical flaw: absent FQNs get `len(order_index)` as their sort position. If `order_index` contains any present-key value >= `len(order_index)`, the absent FQN's tuple sorts BEFORE that present key — violating the spec guarantee that absent FQNs must sort AFTER all present FQNs.

However, in the actual codebase, `order_index` is always constructed as:
```python
order_index = {fqn: i for i, fqn in enumerate(topdown)}
```
This produces consecutive values 0, 1, ..., n-1 where n = len(order_index). Since absent keys get position n > n-1 (the maximum present value), the bug cannot manifest through normal package usage.

The bug would be triggerable if `order_index` were ever constructed with non-consecutive or sparse values.

### Inputs

| Parameter | Value |
|-----------|-------|
| order_index | `{"alpha": 100, "beta": 200}` |
| fqn (absent) | `"gamma"` |

### Expected (spec-correct) Output

After sorting with _order_key, `"gamma"` should appear **after** `"alpha"` and `"beta"`: sorted order `["alpha", "beta", "gamma"]`

### Actual (buggy) Output

After sorting with _order_key, `"gamma"` appears **before** `"alpha"` and `"beta"`: sorted order `["gamma", "alpha", "beta"]` — because `len(order_index)` = 2 < 100, 200

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# The _order_key function is a local closure inside _update_specs_for_intent
# and cannot be called directly. The logic can be reproduced externally:
_order_key = lambda fqn, oi: (oi.get(fqn, len(oi)), fqn)
oi = {"alpha": 100, "beta": 200}
sort_keys = [_order_key("alpha", oi), _order_key("beta", oi), _order_key("gamma", oi)]
result = sorted(sort_keys)
# actual (buggy) output: [('gamma', 2), ('alpha', 100), ('beta', 200)]
# expected (correct) output: [('alpha', 100), ('beta', 200), ('gamma', 2)]
```

---

## Probe Script

```python
"""
Probe script for bug: src--incremental_reasoner-py--_order_key

The _order_key function (line 1622 of src/incremental_reasoner.py) is a local
closure inside _update_specs_for_intent. It accesses order_index via closure.

Bug: _order_key returns (order_index.get(fqn, len(order_index)), fqn).
For absent FQNs, position = len(order_index). If any present FQN has a value
>= len(order_index), the absent FQN sorts BEFORE that present FQN, violating
the spec that absent FQNs must sort AFTER all present FQNs.

In the actual code, order_index is always constructed as:
    order_index = {fqn: i for i, fqn in enumerate(topdown)}
producing consecutive values 0..n-1, so the bug cannot manifest in practice.
"""
import sys


def _order_key_buggy(fqn, order_index):
    """Exact replica of the buggy _order_key logic (line 1622-1623)."""
    return (order_index.get(fqn, len(order_index)), fqn)


def test_bug_logic():
    """Demonstrate the bug with sparse order_index."""
    order_index = {"alpha": 100, "beta": 200}
    absent_fqns = ["gamma", "delta", "epsilon"]

    sort_keys = []
    for fqn in order_index:
        sort_keys.append(_order_key_buggy(fqn, order_index))
    for fqn in absent_fqns:
        sort_keys.append(_order_key_buggy(fqn, order_index))

    sorted_keys = sorted(sort_keys)
    sorted_names = [name for _, name in sorted_keys]

    absent_positions = []
    present_positions = []
    for i, name in enumerate(sorted_names):
        if name in absent_fqns:
            absent_positions.append(i)
        else:
            present_positions.append(i)

    bug_triggered = bool(absent_positions and present_positions and min(absent_positions) < max(present_positions))
    return bug_triggered, order_index, sorted_names, absent_positions, present_positions


def test_safe_construction():
    """Demonstrate the actual code construction does NOT trigger the bug."""
    topdown = ["alpha", "beta", "gamma"]
    order_index = {fqn: i for i, fqn in enumerate(topdown)}
    absent_fqns = ["delta", "epsilon"]

    sort_keys = []
    for fqn in order_index:
        sort_keys.append(_order_key_buggy(fqn, order_index))
    for fqn in absent_fqns:
        sort_keys.append(_order_key_buggy(fqn, order_index))

    sorted_keys = sorted(sort_keys)
    sorted_names = [name for _, name in sorted_keys]

    absent_positions = []
    present_positions = []
    for i, name in enumerate(sorted_names):
        if name in absent_fqns:
            absent_positions.append(i)
        else:
            present_positions.append(i)

    bug_triggered = bool(absent_positions and present_positions and min(absent_positions) < max(present_positions))
    return bug_triggered, order_index, sorted_names


def main():
    triggered, idx, names, apos, ppos = test_bug_logic()
    print(f"Test 1 (sparse order_index = {idx}):")
    print(f"  Sorted order: {names}")
    if triggered:
        print(f"  CONFIRMED: absent FQNs at positions {apos} sort BEFORE present FQNs at {ppos}")
        print(f"  Violates spec: absent FQNs must sort AFTER all present FQNs.")
    else:
        print("  NOT CONFIRMED: absent FQNs sort correctly.")

    triggered2, idx2, names2 = test_safe_construction()
    print(f"\nTest 2 (consecutive order_index = {idx2}):")
    print(f"  Sorted order: {names2}")
    if triggered2:
        print("  CONFIRMED: bug manifested even with safe construction!")
    else:
        print("  Absent FQNs sort correctly after all present FQNs.")
        print("  Actual code behavior: bug is latent, NOT triggerable in practice.")

    print("\n---")
    print("The _order_key function has a LOGICAL BUG: absent keys get")
    print("len(order_index) as position, which can be smaller than present key values.")
    print("Cannot trigger through public API because order_index is always")
    print("constructed with consecutive 0..n-1 values via enumerate().")
    print("\nNOT CONFIRMED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
```

### Probe Output

```
Test 1 (sparse order_index = {'alpha': 100, 'beta': 200}):
  Sorted order: ['delta', 'epsilon', 'gamma', 'alpha', 'beta']
  CONFIRMED: absent FQNs at positions [0, 1, 2] sort BEFORE present FQNs at [3, 4]
  Violates spec: absent FQNs must sort AFTER all present FQNs.

Test 2 (consecutive order_index = {'alpha': 0, 'beta': 1, 'gamma': 2}):
  Sorted order: ['alpha', 'beta', 'gamma', 'delta', 'epsilon']
  Absent FQNs sort correctly after all present FQNs.
  Actual code behavior: bug is latent, NOT triggerable in practice.

---
The _order_key function has a LOGICAL BUG: absent keys get
len(order_index) as position, which can be smaller than present key values.
Cannot trigger through public API because order_index is always
constructed with consecutive 0..n-1 values via enumerate().

NOT CONFIRMED
```
