# Bug Report: _parse_caller

**Source file:** `src/call_graph_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When value is not a dict, raises ValueError whose message contains source
  - When value is a dict but neither a non-empty fqn string nor a non-empty callsite_names list can be extracted from it, raises ValueError whose message contains source
  - Otherwise, returns a CallerSelector where at least one of fqn or callsite_names is non-empty
  - The returned CallerSelector's fqn is the canonical normalized form of the string from value["fqn"] when that key holds a non-empty string; otherwise fqn is the empty string
  - The returned CallerSelector's callsite_names is a tuple containing every non-empty string element from value["callsite_names"] when that key holds a list value; otherwise callsite_names is an empty tuple

---

### Actual Behavior

If `value` is not a dictionary, raise ValueError with message `f"{source}: missing object 'caller'"`. Otherwise, let `d = value`. Let `raw_fqn = d.get("fqn", "")` and `raw_calls = d.get("callsite_names", [])`. 

- If `raw_fqn` is present (key exists and value is not `None`) and is neither a string nor empty, a ValueError is raised by `_optional_string`. 
- If `raw_calls` is not a list, a ValueError is raised by `_string_list`. 
- If `raw_calls` is a list any element of which is neither a string nor empty, a ValueError is raised by `_string_list`. 

Otherwise, after successful processing:
  - `fqn_str = raw_fqn.strip()` when `raw_fqn` is a non-empty string, else `""`.
  - `fqn = normalize_fqn_label(fqn_str)` if `fqn_str`, else `""`.
  - `callsite_names = tuple(e.strip() for e in raw_calls if isinstance(e, str) and e.strip())`.
  - If both `fqn` and `callsite_names` are empty, raise ValueError with message `f"{source}: at least one of 'caller.fqn' or 'caller.callsite_names' must be non-empty"`.
  - Otherwise, return `CallerSelector(fqn=fqn, callsite_names=callsite_names)`, where `fqn` is either empty or a normalized fullyqualified name, `callsite_names` is a tuple of nonempty strings, and at least one of them is nonempty.

Formal logic:
Pre:  value  Any,  source  str
Post: (isinstance(value, dict)  raised(ValueError, "{source}: missing object 'caller'"))
 (isinstance(value, dict) 
    let D = value in
    let fqn_in = D.get("fqn", ""), calls_in = D.get("callsite_names", []) in
    ( (fqn_in  None  isinstance(fqn_in, str)  fqn_in  "")  raised(ValueError) ) 
    ( (calls_in is not list)  raised(ValueError) ) 
    ( (calls_in is list   e  calls_in : e  None  isinstance(e, str)  e  "")  raised(ValueError) ) 
    ( let fqn_str = (fqn_in.strip() if isinstance(fqn_in, str) and fqn_in.strip() else ""),
          fqn = (normalize_fqn_label(fqn_str) if fqn_str else ""),
          cs  = tuple(e.strip() for e in calls_in if isinstance(e, str) and e.strip()) in
      (fqn = ""  cs = ()  raised(ValueError, "{source}: at least one of ... must be non-empty"))
      (fqn  ""  cs  ()  returns CallerSelector(fqn=fqn, callsite_names=cs))
    )
  )

---

## Code Evidence

Line 4: fqn = _optional_string(value.get("fqn", ""), "caller.fqn", source)

---

## Trigger Condition

The code raises a ValueError when "fqn" holds a nonstring value (e.g., 1) because `_optional_string` rejects nonstring inputs, even when `callsite_names` provides a nonempty list. The specification requires that a nonstring value for "fqn" be treated as an empty fqn (since the key does not hold a nonempty string) and that the function should still return a CallerSelector if `callsite_names` is nonempty.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| value["fqn"] | `1` (integer, not a string) |
| value["callsite_names"] | `["test_fn"]` (nonempty list of strings) |
| source | (path to temp JSON file) |

### Expected (spec-correct) Output

A `CallerSelector` with `fqn=""` and `callsite_names=("test_fn",)` — because a non-string `fqn` does not qualify as a "non-empty fqn string", so fqn defaults to the empty string, and `callsite_names` is nonempty.

### Actual (buggy) Output

`ValueError: {source}: 'caller.fqn' must be a string` — `_optional_string` rejects the integer value `1` because it is neither `None` nor a `str`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
import sys
sys.path.insert(0, ".")

from src.call_graph_edges import load_call_edges

payload = {
    "edges": [{
        "caller": {"fqn": 1, "callsite_names": ["test_fn"]},
        "callee": {"fqn": "some::callee::func"},
    }]
}

fd, tmp = tempfile.mkstemp(suffix=".json")
with os.fdopen(fd, "w") as f:
    json.dump(payload, f)

try:
    load_call_edges(tmp)  # ValueError: 'caller.fqn' must be a string
finally:
    os.unlink(tmp)
// actual (buggy) output: ValueError: .../tmpXXX.json:edges[1]: 'caller.fqn' must be a string
// expected (correct) output: [CallEdge(caller=CallerSelector(fqn='', callsite_names=('test_fn',)), ...)]
```

---

## Probe Script

```python
"""Probe script for bug src--call_graph_edges-py--_parse_caller.

Bug claim: _parse_caller raises ValueError when "fqn" holds a non-string value
(e.g., integer 1) because _optional_string rejects non-string inputs, even when
"callsite_names" provides a nonempty list. Per spec, a non-string fqn should be
treated as empty, and the function should still return a CallerSelector when
callsite_names is nonempty.
"""

import json
import os
import sys
import tempfile

# Ensure the project's src/ directory is on the Python path so the public
# entry-point import works from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

# Build a minimal JSON edge file with fqn = 1 (non-string, triggers the bug)
# and a nonempty callsite_names so the spec says it should succeed.
payload = {
    "edges": [
        {
            "caller": {
                "fqn": 1,
                "callsite_names": ["test_fn"],
            },
            "callee": {
                "fqn": "some::callee::func",
            },
        }
    ]
}

fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_parse_caller_")
try:
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f)

    # Spec-correct behavior: fqn=1 should be treated as empty, callsite_names
    # is nonempty → should return a CallEdge with CallerSelector("", ("test_fn",)).
    # Actual (buggy) behavior: _optional_string raises ValueError on non-string.
    try:
        result = load_call_edges(tmp_path)
        # If we reach here, the code did NOT raise → NOT CONFIRMED
        print(
            f"NOT CONFIRMED — load_call_edges succeeded unexpectedly, "
            f"returned {len(result)} edge(s)"
        )
    except ValueError as exc:
        # Bug reproduced: ValueError was raised for non-string fqn
        print(f"CONFIRMED — actual (buggy): ValueError raised: {exc}")
    except Exception as exc:
        # Unexpected error type
        print(f"NOT CONFIRMED — unexpected exception: {type(exc).__name__}: {exc}")
finally:
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
```

### Probe Output

```
CONFIRMED — actual (buggy): ValueError raised: /tmp/probe_parse_caller__0gw7oqd.json:edges[1]: 'caller.fqn' must be a string
```
