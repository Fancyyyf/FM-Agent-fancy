# Bug Report: _parse_caller

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_parse_caller.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a CallerSelector constructed from the caller data in value. Raises ValueError whose message contains source when value is None, is not a dict, or has both 'fqn' (empty or absent) and 'callsite_names' (empty or absent). When value is a valid dict: the 'fqn' key, if present and non-empty, is converted to FM-Agent canonical FQN form and used as the fqn field; the 'callsite_names' key, if present, is converted to a tuple of strings and used as the callsite_names field. At least one of the two fields in the returned CallerSelector is non-empty.

---

### Actual Behavior

If value is not a dict, a ValueError is raised with message containing source and "missing object 'caller'". Otherwise, let v_fqn = value.get("fqn", "") and v_callsite = value.get("callsite_names", []). If v_fqn is a non-empty, non-string value, a ValueError is raised with message containing source and "caller.fqn". If v_callsite is not a valid sequence of strings, a ValueError is raised with message containing source and "caller.callsite_names". Let fqn = normalize_fqn_label(v_fqn) if v_fqn is a non-empty string, else empty string; let callsite_names be the tuple of strings from v_callsite (empty tuple if absent or empty). If fqn is empty and callsite_names is empty, a ValueError is raised with message "source: at least one of 'caller.fqn' or 'caller.callsite_names' must be non-empty". Otherwise, the function returns CallerSelector(fqn, callsite_names). Formally: ( isinstance(value, dict)   ValueError  msg = source + ": missing object 'caller'")  (isinstance(value, dict)  v_fqn  ""   isinstance(v_fqn, str)   ValueError  msg contains source  msg contains "caller.fqn")  (isinstance(value, dict)   valid_string_sequence(v_callsite)   ValueError  msg contains source  msg contains "caller.callsite_names")  (isinstance(value, dict)  fqn = (normalize_fqn_label(v_fqn) if v_fqn is a non-empty string else "")  callsite_names = tuple(v_callsite) if valid_string_sequence(v_callsite) else already raised  (fqn = ""  callsite_names = ())   ValueError  msg = source + ": at least one of 'caller.fqn' or 'caller.callsite_names' must be non-empty")  (otherwise  returns CallerSelector(fqn, callsite_names) with fqn = (normalize_fqn_label(v_fqn) if v_fqn  "" and is string else "") and callsite_names = tuple of strings from v_callsite, and  (fqn = ""  callsite_names = ()))

---

## Code Evidence

Line 5: fqn = _optional_string(value.get("fqn", ""), "caller.fqn", source)

---

## Trigger Condition

The code raises a ValueError whenever 'fqn' is present but has a non-string type (e.g., integer 123). The specification only permits ValueError when value is None, not a dict, or both 'fqn' (empty/absent) and 'callsite_names' (empty/absent). For the valid dict {"fqn": 123} the specification requires returning a CallerSelector, but the code raises a ValueError instead.

---

## How to trigger the bug

When `_parse_caller` (called via `load_call_edges` -> `_edge_from_mapping`) receives a caller dict where `"fqn"` is a non-string truthy value such as an integer, `_optional_string` rejects it with a `ValueError`. The specification requires that any non-empty fqn value be converted to its string representation and normalized, not rejected.

### Inputs

| Parameter | Value |
|-----------|-------|
| value (caller dict) | `{"fqn": 123}` |
| source | `"/path/to/file.json:edges[1]"` |

### Expected (spec-correct) Output

`CallerSelector(fqn=normalize_fqn_label("123"), callsite_names=())`

### Actual (buggy) Output

`ValueError("/path/to/file.json:edges[1]: 'caller.fqn' must be a string")`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
from src.call_graph_edges import load_call_edges

tmpdir = tempfile.mkdtemp()
json_path = os.path.join(tmpdir, "test.json")
with open(json_path, "w") as f:
    json.dump({"edges": [{"caller": {"fqn": 123}}]}, f)

try:
    result = load_call_edges(json_path)
    # Should succeed per spec — but it raises instead
except ValueError as e:
    print(f"ValueError: {e}")
# actual (buggy) output: ValueError: ...: 'caller.fqn' must be a string
# expected (correct) output: list of CallEdge with caller.fqn="123"
```

---

## Probe Script

```python
import sys
import tempfile
import os
import json

# Ensure the repo root is on sys.path so 'src' is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.call_graph_edges import load_call_edges, CallerSelector

    # Create temp dir and JSON file with integer fqn (should be accepted per spec)
    tmpdir = tempfile.mkdtemp()
    json_path = os.path.join(tmpdir, "test_edges.json")
    with open(json_path, "w") as f:
        json.dump({"edges": [{"caller": {"fqn": 123}}]}, f)

    try:
        result = load_call_edges(json_path)

        # If we get here, the code did NOT raise — check if fqn was converted from int
        if result and len(result) > 0:
            actual = result[0].caller.fqn
            print(
                "NOT CONFIRMED — load_call_edges returned successfully"
                f" (unexpected); caller.fqn={actual!r}"
            )
        else:
            print("NOT CONFIRMED — load_call_edges returned empty result")
    except ValueError as e:
        err_msg = str(e)
        if "caller.fqn" in err_msg or "must be a string" in err_msg:
            print(
                "CONFIRMED — ValueError raised for integer fqn:"
                f" {err_msg} | expected: CallerSelector with fqn='123'"
            )
        else:
            print(
                f"NOT CONFIRMED — unexpected ValueError (not fqn-related): {err_msg}"
            )
    finally:
        # Clean up temp files
        if os.path.exists(json_path):
            os.unlink(json_path)
        if os.path.exists(tmpdir):
            os.rmdir(tmpdir)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — ValueError raised for integer fqn: /tmp/tmp0wrczopb/test_edges.json:edges[1]: 'caller.fqn' must be a string | expected: CallerSelector with fqn='123'
```
