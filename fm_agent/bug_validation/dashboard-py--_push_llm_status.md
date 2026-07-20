# Bug Report: _push_llm_status

**Source file:** `dashboard-py/_push_llm_status.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- A new record is appended to self.llm_statuses.
  - The record contains the following fields:
      * "time": "HH:MM:SS" string formatted from ts when ts is
        truthy; empty string when ts is falsy.
      * "source": the given source value.
      * "label": the given label value, defaulting to "llm_call"
        when label is falsy.
      * "status": the given status value, defaulting to "?" when
        status is falsy.
      * "model": the given model value.
      * "code": the given code value, defaulting to the status
        value when code is falsy; if status is also falsy,
        defaults to "?".
      * "detail": the given detail value.
  - self.llm_statuses never exceeds a fixed maximum length; when the
    append would exceed the maximum, the oldest entry is evicted.

---

### Actual Behavior

After the method executes, no exception is raised. The sequence `self.llm_statuses` has been updated to contain a new dictionary as its last element, with fields assembled from the parameters. Let `old` be the value of `self.llm_statuses` immediately before the call, `new` be its value after the call, and `capacity` the fixed maximum length of the sequence (the eviction threshold). The new dictionary `entry` is defined as:

`entry = {
  "time": ts.strftime("%H:%M:%S") if ts is not None else "",
  "source": source,
  "label": label if label else "llm_call",
  "status": status if status else "?",
  "model": model,
  "code": code if code else (status if status else "?"),
  "detail": detail
}`

Post-conditions on the sequence:
- If `len(old) < capacity`:
    `new == old + [entry]` and `len(new) == len(old) + 1`.
- If `len(old) == capacity`:
    `new == old[1:] + [entry]` and `len(new) == capacity`.
- The new element is always at index `len(new) - 1`.
- All other objects (including `self`, `ts`, and the string parameters) remain unchanged, and no side effects occur outside `self.llm_statuses`.

---

## Code Evidence

Line 1: def _push_llm_status(self, ts, source, label, status, model=None, code=None, detail=None): ... The method (as described in post-condition A) only evicts the oldest entry when len(old) == capacity; it does not evict when len(old) > capacity. Consequently, if the sequence is already over capacity, appending another entry violates the invariant.

---

## Trigger Condition

The specification requires that the sequence never exceeds the maximum length, and when an append would exceed it, the oldest entry is evicted. Post-condition A guarantees eviction only if len(old) == capacity, leaving cases where len(old) > capacity unhandled. In such a case, the sequence grows beyond the limit, violating requirement B.

---

## How to trigger the bug

The bug claim is that `_push_llm_status` does not handle the case where `len(old) > capacity`, allowing the deque to grow beyond its maximum length. However, `self.llm_statuses` is a `collections.deque(maxlen=LLM_STATUS_WINDOW=80)`. Python's `deque.append()` with `maxlen` set automatically evicts the oldest item from the left when the deque is full — regardless of whether `len(old)` equals or exceeds `capacity`. In fact, it is impossible for a bounded deque to exceed its maxlen through `append()` alone; Python's C implementation guarantees this invariant.

The perceived gap is in the post-condition specification (which only covers `len(old) == capacity`), not in the actual code behavior. The code is correct; the spec analysis is incomplete.

### Inputs

| Parameter | Value |
|-----------|-------|
| self.llm_statuses | `deque(maxlen=80)` filled with 80 entries (at capacity) |
| ts | `datetime(2025, 1, 15, 12, 30, 45)` |
| source | `"test"` |
| label | `"overflow"` |
| status | `"success"` |
| model | `"test-model"` |

### Expected (spec-correct) Output

`len(self.llm_statuses) == 80` (oldest entry evicted, new entry appended)

### Actual (buggy) Output

`len(self.llm_statuses) == 80` (oldest entry evicted by deque, same as expected)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import State
from datetime import datetime
from collections import deque

state = State(".")
LLM_STATUS_WINDOW = 80

# Fill to capacity
state.llm_statuses.clear()
for i in range(LLM_STATUS_WINDOW):
    state._push_llm_status(datetime.now(), "test", f"l{i}", "success", model="m")

# Push one more when at capacity
state._push_llm_status(datetime.now(), "test", "overflow", "success", model="m")
print(len(state.llm_statuses))
# actual (buggy) output: 80
# expected (correct) output: 80

# Even with direct deque.append() exceeding capacity
state.llm_statuses.clear()
for i in range(LLM_STATUS_WINDOW + 10):
    state.llm_statuses.append({"time": "", "source": "t", "label": str(i), "status": "ok", "model": "m", "code": "200", "detail": None})
print(len(state.llm_statuses))
# actual (buggy) output: 80
# expected (correct) output: 80
```

---

## Probe Script

```python
"""Probe script for _push_llm_status bug validation.

Bug: The _push_llm_status method allegedly only evicts when len(old) == capacity
but not when len(old) > capacity, potentially exceeding the max length.
Using Python's collections.deque with maxlen, we test whether exceeding
the capacity boundary is actually possible.
"""
import sys
import os
from datetime import datetime
from collections import deque

# Script is at fm_agent/bug_validation/probe_*.py; repo root is 3 levels up
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from dashboard import State

    LLM_STATUS_WINDOW = 80  # from dashboard.py

    repo_root = REPO_ROOT
    state = State(repo_root)
    ts = datetime(2025, 1, 15, 12, 30, 45)

    # Fill to exactly capacity
    state.llm_statuses.clear()
    for i in range(LLM_STATUS_WINDOW):
        state._push_llm_status(ts, "test", f"label{i}", "success", model="test-model")

    assert len(state.llm_statuses) == LLM_STATUS_WINDOW, \
        f"Expected {LLM_STATUS_WINDOW} entries at capacity, got {len(state.llm_statuses)}"

    # Push one more -- should stay at capacity (oldest evicted by deque)
    first_entry_label = state.llm_statuses[0]["label"]
    state._push_llm_status(ts, "test", "overflow", "success", model="test-model")

    len_after = len(state.llm_statuses)
    new_first_label = state.llm_statuses[0]["label"]

    if len_after > LLM_STATUS_WINDOW:
        print(f'CONFIRMED -- capacity exceeded: len={len_after} > {LLM_STATUS_WINDOW}')
        sys.exit(0)

    # Check eviction: oldest should be gone
    if first_entry_label == new_first_label:
        print(f'CONFIRMED -- oldest entry not evicted when at capacity (label: {new_first_label})')
        sys.exit(0)

    # Test: append more items than maxlen directly to the deque
    state.llm_statuses.clear()
    for i in range(LLM_STATUS_WINDOW + 10):
        state.llm_statuses.append(
            {"time": "12:00:00", "source": "test", "label": f"l{i}",
             "status": "success", "model": "m", "code": "200", "detail": None}
        )

    if len(state.llm_statuses) > LLM_STATUS_WINDOW:
        print(f'CONFIRMED -- deque append did not evict excess: len={len(state.llm_statuses)} > {LLM_STATUS_WINDOW}')
        sys.exit(0)

    # Final test: push via _push_llm_status on an already-full deque
    state.llm_statuses.clear()
    for i in range(LLM_STATUS_WINDOW):
        state._push_llm_status(ts, "test", f"label{i}", "success", model="test-model")

    state._push_llm_status(ts, "test", "final", "success", model="test-model")
    if len(state.llm_statuses) > LLM_STATUS_WINDOW:
        print(f'CONFIRMED -- _push_llm_status exceeded capacity: len={len(state.llm_statuses)} > {LLM_STATUS_WINDOW}')
        sys.exit(0)

    # All checks passed
    print(f'NOT CONFIRMED -- deque maxlen={LLM_STATUS_WINDOW} correctly enforces capacity limit. '
          f'oldest evicted (was "{first_entry_label}", now "{new_first_label}"), '
          f'final len={len(state.llm_statuses)}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — deque maxlen=80 correctly enforces capacity limit. oldest evicted (was "label0", now "label1"), final len=80
```
