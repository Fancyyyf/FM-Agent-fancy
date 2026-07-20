# Bug Report: _resolve_extra_call_edges

**Source file:** `fm_agent/extracted_functions/src/generate_topdown_layers-py/_resolve_extra_call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns (by_caller_fqn, by_callsite): two dict-like mappings that return
    an empty list for any key not explicitly present
  - by_caller_fqn: maps each caller FQN (from edge.caller.fqn) to a list of
    resolved-edge objects; a caller FQN appears as a key iff it is a member of
    phase_fqns AND at least one supplied edge whose callee.fqn is a member of
    known_fqns carries that exact caller FQN
  - by_callsite: maps each callsite name string to a list of resolved-edge
    objects; a callsite name appears as a key iff it is a valid source-code
    identifier (begins with an ASCII letter or underscore, followed by zero or
    more ASCII alphanumeric characters or underscores) AND at least one supplied
    edge whose callee.fqn is a member of known_fqns lists that callsite in
    edge.caller.callsite_names
  - A single supplied edge can produce entries in both by_caller_fqn (via its
    caller.fqn) and by_callsite (via each of its caller.callsite_names),
    independently
  - When extra_call_edges is None or empty, both returned mappings contain no
    entries
  - An edge whose callee.fqn is NOT a member of known_fqns produces NO entries
    in either returned mapping (the edge is silently excluded)
  - A caller FQN from edge.caller.fqn that is NOT a member of phase_fqns
    produces NO entry in by_caller_fqn for that edge (the edge is silently
    excluded with respect to that caller FQN, but may still produce entries in
    by_callsite)
  - Each resolved-edge object in the returned lists carries at minimum: the
    callee FQN, a tuple of supplemental info names from the original edge's
    callee.info_names, and a source identifier

---

### Actual Behavior

If `extra_call_edges` is None or empty, the function returns a tuple of two empty `defaultdict(list)` objects. Otherwise, let P = set(phase_fqns) and K = set(known_fqns). For each edge e in extra_call_edges, if e.callee.fqn  K, a _ResolvedExtraEdge r is created with callee_fqn = e.callee.fqn, info_names = tuple(e.callee.info_names), source = e.source. Then, if e.caller.fqn is truthy and e.caller.fqn  P, r is appended to by_caller_fqn[e.caller.fqn]; otherwise a debug log message is emitted. For each callsite c in e.caller.callsite_names, if re.fullmatch(r"[A-Za-z_]\w*", c) succeeds, r is appended to by_callsite[c]; otherwise a warning log message is emitted. If e.callee.fqn  K, a warning log message is emitted and the edge contributes no entries. The returned by_caller_fqn is a defaultdict(list) that maps exactly each caller FQN f for which at least one qualifying edge satisfied the above conditions to the list of corresponding resolved edges, preserving the iteration order of extra_call_edges. The returned by_callsite is a defaultdict(list) that maps exactly each valid callsite name c to the list of resolved edges from qualifying edges containing that callsite, in the order edges were processed. Logging side effects are not reflected in the return value.

---

## Code Evidence

Line 24: if edge.caller.fqn:

---

## Trigger Condition

The code uses a truthiness check on edge.caller.fqn, skipping empty strings or other falsy values even if they are members of phase_fqns. The specification requires that any caller FQN present in phase_fqns appears as a key, without exempting falsy values.

---

## How to trigger the bug

The bug occurs when `edge.caller.fqn` is a falsy value (e.g., empty string `""`) that is legitimately present in `phase_fqns`. The truthiness check `if edge.caller.fqn:` at line 413 (line 24 in the extracted version) evaluates to `False` for the empty string, causing the entire `by_caller_fqn` entry to be skipped — even though the spec requires the empty string to appear as a key whenever it is a member of `phase_fqns`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `extra_call_edges` | `[CallEdge(caller=CallerSelector(fqn="", callsite_names=()), callee=CalleeTarget(fqn="callee_func", info_names=()), source="test")]` |
| `phase_fqns` | `[""]` |
| `known_fqns` | `["callee_func"]` |

### Expected (spec-correct) Output

`by_caller_fqn[""]` = `[_ResolvedExtraEdge(callee_fqn="callee_func", info_names=(), source="test")]`

### Actual (buggy) Output

`by_caller_fqn` has no keys (empty); the `""` key is missing.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import _resolve_extra_call_edges
from src.call_graph_edges import CallEdge, CallerSelector, CalleeTarget

edge = CallEdge(
    caller=CallerSelector(fqn="", callsite_names=()),
    callee=CalleeTarget(fqn="callee_func", info_names=()),
    source="test",
)

by_caller_fqn, by_callsite = _resolve_extra_call_edges(
    [edge],
    phase_fqns=[""],
    known_fqns=["callee_func"],
)

# Expected: "" in by_caller_fqn → True
# Actual:   "" in by_caller_fqn → False (BUG)
print("" in by_caller_fqn)  # False — should be True
```

---

## Probe Script

```python
"""Probe script for bug: _resolve_extra_call_edges truthiness check on edge.caller.fqn.

Bug: The code uses 'if edge.caller.fqn:' (truthiness check) before checking
membership in phase_fqns. This skips falsy values (like empty string) even
when they ARE members of phase_fqns. The spec requires that any caller FQN
present in phase_fqns appears as a key, without exempting falsy values.
"""

import sys

try:
    from src.generate_topdown_layers import _resolve_extra_call_edges, _ResolvedExtraEdge
    from src.call_graph_edges import CallEdge, CallerSelector, CalleeTarget

    # Construct an edge where caller.fqn is an empty string (falsy).
    # The callee.fqn must be in known_fqns for the edge to be processed at all.
    edge = CallEdge(
        caller=CallerSelector(fqn="", callsite_names=()),
        callee=CalleeTarget(fqn="callee_func", info_names=()),
        source="test",
    )

    # phase_fqns includes the empty string — the spec says it MUST appear as a key.
    phase_fqns = [""]
    known_fqns = ["callee_func"]

    by_caller_fqn, by_callsite = _resolve_extra_call_edges(
        [edge], phase_fqns=phase_fqns, known_fqns=known_fqns
    )

    # Spec-correct behavior: "" should be a key in by_caller_fqn
    # Buggy behavior: "" is NOT a key because 'if edge.caller.fqn:' is False for ""
    has_empty_key = "" in by_caller_fqn

    if has_empty_key:
        entries = by_caller_fqn[""]
        actual_repr = repr([(e.callee_fqn, e.info_names) for e in entries])
        print(f"NOT CONFIRMED — bug not triggered: empty string key present with {len(entries)} entry(ies): {actual_repr}")
    else:
        # Bug confirmed: empty string is in phase_fqns but NOT in by_caller_fqn
        all_keys = list(by_caller_fqn.keys())
        print(f"CONFIRMED — actual: by_caller_fqn has keys {all_keys!r} | expected: key '' (empty string) should be present because '' is in phase_fqns")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: by_caller_fqn has keys [] | expected: key '' (empty string) should be present because '' is in phase_fqns
```
