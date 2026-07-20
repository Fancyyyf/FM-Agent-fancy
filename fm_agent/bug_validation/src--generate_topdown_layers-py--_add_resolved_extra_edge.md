# Bug Report: _add_resolved_extra_edge

**Source file:** `src/generate_topdown_layers.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True if and only if edge.callee_fqn was not a member of all_callees_map[caller_fqn] prior to the call
- Returns False without modifying any map when caller_fqn equals edge.callee_fqn (self-edge)
- After the call, edge.callee_fqn is a member of all_callees_map[caller_fqn]
- After the call, every string from edge.info_names is a member of edge_aliases_map[edge.callee_fqn][caller_fqn]
- If edge.callee_fqn is a member of phase_fqns, then edge.callee_fqn is added to callees_map[caller_fqn] and caller_fqn is added to callers_map[edge.callee_fqn]
- If edge.callee_fqn is not a member of phase_fqns, neither callees_map nor callers_map is modified

---

### Actual Behavior

After execution, one of the following mutually exclusive scenarios holds, given the inputs and initial state (pre-state). Let P = (caller_fqn == edge.callee_fqn), S = (edge.callee_fqn in phase_fqns), K1 = (caller_fqn in callees_map), K2 = (edge.callee_fqn in callers_map), info = set(edge.info_names), and old_size = |all_callees_map_pre[caller_fqn]|.

1. If P is true: all data structures remain unchanged (equal to their pre-state values), and the function returns False.

2. If P is false:
   The sets all_callees_map[caller_fqn] and edge_aliases_map[edge.callee_fqn][caller_fqn] are always modified:
     all_callees_map_post[caller_fqn] = all_callees_map_pre[caller_fqn] ∪ {edge.callee_fqn}
     edge_aliases_map_post[edge.callee_fqn][caller_fqn] = edge_aliases_map_pre[edge.callee_fqn][caller_fqn] ∪ info
   a) If S is false:
        callees_map_post = callees_map_pre
        callers_map_post = callers_map_pre
        return value = (edge.callee_fqn ∉ all_callees_map_pre[caller_fqn])
   b) If S is true and K1 is true and K2 is true:
        callees_map_post[caller_fqn] = callees_map_pre[caller_fqn] ∪ {edge.callee_fqn}
        callers_map_post[edge.callee_fqn] = callers_map_pre[edge.callee_fqn] ∪ {caller_fqn}
        all other entries unchanged
        return value = (edge.callee_fqn ∉ all_callees_map_pre[caller_fqn])
   c) If S is true and K1 is true and K2 is false:
        callees_map_post[caller_fqn] = callees_map_pre[caller_fqn] ∪ {edge.callee_fqn}
        callers_map_post = callers_map_pre (unchanged)
        a KeyError exception is raised; function terminates abnormally, no return value.
   d) If S is true and K1 is false:
        callees_map_post = callees_map_pre (unchanged)
        callers_map_post = callers_map_pre (unchanged)
        a KeyError exception is raised; function terminates abnormally, no return value.

All other data structures (including other entries in the maps) remain unchanged from their pre-state values.

---

## Code Evidence

Line 18: `callees_map[caller_fqn].add(callee_fqn)`

The function accesses `callees_map[caller_fqn]` assuming `caller_fqn` is already a key. When `callee_fqn ∈ phase_fqns` but `caller_fqn ∉ callees_map`, this line raises `KeyError` instead of returning a boolean as the specification requires.

---

## Trigger Condition

The specification requires adding edge.callee_fqn to callees_map[caller_fqn] and returning a boolean, but the code raises KeyError because caller_fqn is not a key in callees_map, violating the postcondition.

---

## How to trigger the bug

The bug appears when `edge.callee_fqn` is in `phase_fqns` (S = true) but `caller_fqn` is NOT a key in `callees_map` (K1 = false). In this case, the code at line 458 (`callees_map[caller_fqn].add(callee_fqn)`) raises `KeyError` because `caller_fqn` is not in `callees_map`. The specification requires the function to add the callee and return a boolean, not to throw an exception.

In the actual codebase, `callees_map` is always created as a `defaultdict(set)` in `_build_call_graph`, so the KeyError is masked — `defaultdict` auto-creates missing keys. However, the function's type contract only requires "mutable dicts mapping FQN strings to mutable sets of FQN strings", not specifically `defaultdict`. If a regular `dict` is passed where `caller_fqn` is absent, the KeyError manifests.

### Inputs

| Parameter | Value |
|-----------|-------|
| `caller_fqn` | `"caller::func"` |
| `edge` | `_ResolvedExtraEdge(callee_fqn="callee::func", info_names=("alias1", "alias2"), source="test")` |
| `phase_fqns` | `{"callee::func"}` |
| `callees_map` | `{}` (regular dict, caller_fqn NOT a key) |
| `callers_map` | `{}` |
| `all_callees_map` | `defaultdict(set)` with `caller_fqn` initialized |
| `edge_aliases_map` | `defaultdict(lambda: defaultdict(set))` with appropriate keys initialized |

### Expected (spec-correct) Output

Returns `True` (boolean). After the call, `callees_map[caller_fqn]` contains `"callee::func"` and `callers_map["callee::func"]` contains `"caller::func"`.

### Actual (buggy) Output

`KeyError('caller::func')` raised at line 458. Function terminates abnormally; no return value.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from collections import defaultdict
from src.generate_topdown_layers import _add_resolved_extra_edge, _ResolvedExtraEdge

caller_fqn = "caller::func"
callee_fqn = "callee::func"
edge = _ResolvedExtraEdge(callee_fqn=callee_fqn, info_names=("alias1",), source="test")

phase_fqns = {callee_fqn}
callees_map = {}          # regular dict — caller_fqn NOT a key
callers_map = {}
all_callees_map = defaultdict(set)
all_callees_map[caller_fqn]
edge_aliases_map = defaultdict(lambda: defaultdict(set))
edge_aliases_map[callee_fqn][caller_fqn]

_add_resolved_extra_edge(
    caller_fqn, edge, phase_fqns,
    callees_map, callers_map, all_callees_map, edge_aliases_map,
)
# actual (buggy) output: KeyError: 'caller::func'
# expected (correct) output: True (boolean), callees_map updated
```

---

## Probe Script

```python
import sys
from collections import defaultdict

try:
    from src.generate_topdown_layers import _add_resolved_extra_edge, _ResolvedExtraEdge
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)


def test_with_regular_dict():
    """Test where callees_map is a regular dict (not defaultdict).
    caller_fqn is NOT in callees_map, callee_fqn IS in phase_fqns -> should KeyError."""
    caller_fqn = "caller::func"
    callee_fqn = "callee::func"

    edge = _ResolvedExtraEdge(
        callee_fqn=callee_fqn,
        info_names=("alias1", "alias2"),
        source="test",
    )

    phase_fqns = {callee_fqn}  # S = true (callee in phase)

    # Regular dict: caller_fqn NOT present (K1 = false)
    callees_map = {}
    callers_map = {}
    all_callees_map = defaultdict(set)
    all_callees_map[caller_fqn]  # pre-condition: must be initialized
    edge_aliases_map = defaultdict(lambda: defaultdict(set))
    edge_aliases_map[callee_fqn][caller_fqn]  # pre-condition: must be initialized

    try:
        result = _add_resolved_extra_edge(
            caller_fqn,
            edge,
            phase_fqns,
            callees_map,
            callers_map,
            all_callees_map,
            edge_aliases_map,
        )
        # If we get here, no KeyError was raised
        print(f"NOT CONFIRMED (regular dict) — no KeyError, result={result!r}")
        return "no_error"
    except KeyError as e:
        print(f"CONFIRMED — actual: KeyError raised | args: {e!r}")
        return "KeyError"
    except Exception as e:
        print(f"ERROR (regular dict): {type(e).__name__}: {e}")
        return f"error: {e}"


def test_with_defaultdict():
    """With defaultdict(set), the function should auto-initialize missing keys.
    This is the actual usage in _build_call_graph."""
    caller_fqn = "caller::func2"
    callee_fqn = "callee::func2"

    edge = _ResolvedExtraEdge(
        callee_fqn=callee_fqn,
        info_names=("a",),
        source="test",
    )

    phase_fqns = {callee_fqn}

    callees_map = defaultdict(set)   # NOT pre-populated with caller_fqn
    callers_map = defaultdict(set)
    all_callees_map = defaultdict(set)
    all_callees_map[caller_fqn]
    edge_aliases_map = defaultdict(lambda: defaultdict(set))
    edge_aliases_map[callee_fqn][caller_fqn]

    try:
        result = _add_resolved_extra_edge(
            caller_fqn,
            edge,
            phase_fqns,
            callees_map,
            callers_map,
            all_callees_map,
            edge_aliases_map,
        )
        # defaultdict auto-creates, so this should succeed
        actual_callees = sorted(callees_map.get(caller_fqn, set()))
        print(f"defaultdict test: result={result!r}, callees_map[caller_fqn]={actual_callees}")
        # Verify spec: callee_fqn IS in phase_fqns, so it should be added
        if callee_fqn in callees_map.get(caller_fqn, set()):
            print("spec_satisfied: callee_fqn added to callees_map[caller_fqn]")
        return "ok"
    except KeyError as e:
        print(f"CONFIRMED (defaultdict) — unexpected KeyError: {e!r}")
        return "KeyError"
    except Exception as e:
        print(f"ERROR (defaultdict): {type(e).__name__}: {e}")
        return f"error: {e}"


# Main
if __name__ == "__main__":
    status = test_with_regular_dict()
    test_with_defaultdict()
    if status == "KeyError":
        pass  # already printed CONFIRMED
    elif status == "no_error":
        print("NOT CONFIRMED — function completed without KeyError on regular dict")
    else:
        print(f"ERROR: unexpected status: {status}")
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: KeyError raised | args: KeyError('caller::func')
defaultdict test: result=True, callees_map[caller_fqn]=['callee::func2']
spec_satisfied: callee_fqn added to callees_map[caller_fqn]
```
