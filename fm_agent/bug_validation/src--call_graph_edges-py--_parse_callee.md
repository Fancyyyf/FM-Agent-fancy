# Bug Report: _parse_callee

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/call_graph_edges-py/_parse_callee.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a CalleeTarget constructed from the callee data
  - The returned CalleeTarget.fqn is a non-empty string
  - The returned CalleeTarget.info_names is a (possibly empty) tuple of strings
  - When value is not a dict, raises a ValueError whose message includes source
  - When value is a dict but does not contain a well-formed "fqn" field yielding a non-empty string, raises an error whose message includes source

---

### Actual Behavior

After execution, the function either raises a ValueError or returns a CalleeTarget instance.

- If value is not a dict, a ValueError is raised with message f"{source}: missing object 'callee'".
- If value is a dict, let fqn_raw = value.get('fqn') and info_names_raw = value.get('info_names', []). Then:
   * When fqn_raw is None, not a string, or a string that after stripping whitespace becomes empty, an error (ValueError) is raised whose message contains source and 'callee.fqn'.
   * Else, when info_names_raw is not a list, an error (ValueError) is raised whose message contains source and 'callee.info_names'.
   * Otherwise, the function returns CalleeTarget(fqn=s, info_names=t) where s is a nonempty string equal to fqn_raw with leading and trailing whitespace removed, and t is a tuple of strings obtained from the elements of info_names_raw (preserving element order and count).

Formally:
(isinstance(value, dict)  
   raises ValueError(msg = source + ": missing object 'callee'"))

(isinstance(value, dict) 
   let f = value.get('fqn'), g = value.get('info_names', []) in
   ((f  None  isinstance(f, str)  strip(f)  "")  
      raises ValueError(msg contains source  msg contains 'callee.fqn'))
   
   (isinstance(g, list)  
      raises ValueError(msg contains source  msg contains 'callee.info_names'))
   
   (returns CalleeTarget(fqn = strip(f), info_names = tuple(map(str, g))))
)

No other side effects occur.

---

## Code Evidence

Line 5: info_names = _string_list(value.get("info_names", []), "callee.info_names", source)

---

## Trigger Condition

The code raises a ValueError when info_names is not a list, but specification B does not list this as an error condition and expects a dict with a well-formed fqn to return a CalleeTarget.

---

## How to trigger the bug

The bug triggers when `_parse_callee` receives a dict with a well-formed `"fqn"` field but where `"info_names"` is not a list (e.g., a string). The internal call to `_string_list` at `src/call_graph_edges.py:190` raises a `ValueError` because `info_names` is not a list, even though the specification only mandates errors for: (1) value not being a dict, (2) fqn not being a well-formed non-empty string. The spec says nothing about non-list info_names being an error condition.

### Inputs

| Parameter | Value |
|-----------|-------|
| value | `{"fqn": "test::target_func", "info_names": "not_a_list_but_a_string"}` |
| source | `"/tmp/probe_parse_callee_<random>.json:edges[1]"` |

### Expected (spec-correct) Output

`CalleeTarget(fqn="test::target_func", info_names=...)` — a CalleeTarget is returned because fqn is well-formed and the spec does not list non-list info_names as an error condition.

### Actual (buggy) Output

`ValueError("/tmp/...json:edges[1]: 'callee.info_names' must be a string array")`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.call_graph_edges import load_call_edges

edge_data = {
    "edges": [{
        "caller": {"callsite_names": ["test_callsite"]},
        "callee": {
            "fqn": "test::target_func",
            "info_names": "not_a_list_but_a_string",
        },
    }]
}
fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_parse_callee_")
try:
    with os.fdopen(fd, "w") as f:
        json.dump(edge_data, f)
    edges = load_call_edges(tmp_path)  # raises ValueError
finally:
    os.unlink(tmp_path)
# actual (buggy) output: ValueError: ...: 'callee.info_names' must be a string array
# expected (correct) output: CalleeTarget returned (spec does not forbid non-list info_names)
```

---

## Probe Script

```python
"""Probe script for _parse_callee bug: non-list info_names raises ValueError
but spec does not list this as an error condition.

Bug: Line 157 passes value.get("info_names", []) to _string_list(), which
raises ValueError when info_names is not a list. Per spec, a dict with a
well-formed fqn should return a CalleeTarget regardless of info_names type.
"""
import json
import os
import sys
import tempfile

try:
    from src.call_graph_edges import load_call_edges

    # Trigger: valid fqn, but info_names is a string instead of a list
    edge_data = {
        "edges": [
            {
                "caller": {
                    "callsite_names": ["test_callsite"],
                },
                "callee": {
                    "fqn": "test::target_func",
                    "info_names": "not_a_list_but_a_string",
                },
            }
        ]
    }

    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_parse_callee_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(edge_data, f)

        edges = load_call_edges(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Per spec, with a well-formed fqn, _parse_callee should return a CalleeTarget
    # (spec does not list non-list info_names as an error condition).
    # If we get here without an error, the bug is NOT confirmed.
    actual = "Returned gracefully (no error)"
    expected = "ValueError raised (spec violation)"
    print(f"NOT CONFIRMED — load_call_edges succeeded: {len(edges)} edge(s) loaded")

except ValueError as e:
    msg = str(e)
    if "callee.info_names" in msg and "string array" in msg:
        actual = f"ValueError: {msg}"
        expected = "CalleeTarget returned (spec says well-formed fqn suffices)"
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — ValueError raised but not about info_names: {msg}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: "ValueError: /tmp/probe_parse_callee_gkkyjr_r.json:edges[1]: 'callee.info_names' must be a string array" | expected: 'CalleeTarget returned (spec says well-formed fqn suffices)'
```
