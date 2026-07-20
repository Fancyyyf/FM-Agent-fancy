# Bug Report: _load_json_edges

**Source file:** `src/call_graph_edges-py/_load_json_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When text is valid JSON that parses to an object containing an "edges"
    key whose value is a list, returns a list of CallEdge objects, one per
    element of that list, in the same order as the "edges" array
  - When the "edges" list is empty, returns an empty list
  - Every returned CallEdge has a callee whose fqn is a non-empty string
  - Every returned CallEdge has a caller object where at least one of fqn
    or callsite_names is non-empty
  - When text is not valid JSON, raises ValueError with a message that
    includes source_path
  - When the parsed JSON value is not a dict, raises ValueError with a
    message that includes source_path
  - When the parsed dict does not contain an "edges" key whose value is a
    list, raises ValueError with a message that includes source_path
  - When any element of the "edges" list is not a dict, raises ValueError
    with a message that includes source_path and the 1-based index of
    the invalid element within the "edges" array

---

### Actual Behavior

The function either raises a ValueError or returns a list of CallEdge objects. If ValueError is raised, the exception's message starts with 'source_path' and indicates the specific violation: if text cannot be decoded as JSON it wraps the json.JSONDecodeError; if the decoded data is not a dict it says 'expected JSON object with an 'edges' list'; if data is a dict but data.get('edges') is not a list it says 'expected an 'edges' list'; if any element of the 'edges' list is not a dict it says 'expected edge object'. If the function returns normally, let D = json.loads(text) (which must succeed). Then D is a dict containing an 'edges' key whose value is a list L (otherwise an earlier ValueError would have been raised). The returned list R satisfies len(R) = len(L) and for every index i in [0, len(L)-1], R[i] = _edge_from_mapping(L[i], f\"{source_path}:edges[{i+1}]\"). Moreover, each R[i] meets the post-condition of _edge_from_mapping: R[i].callee.fqn is a nonempty string, R[i].caller has at least one of fqn or callsite_names nonempty, and R[i].source is set from the mapping's evidence or the source context. Formal logic: (text  valid JSON  ValueError(msg starting with source_path and containing 'invalid JSON'))  (valid JSON  (data := json.loads(text), data  dict)  ValueError(msg starting with source_path and 'expected JSON object with an \'edges\' list'))  (valid JSON  data  dict  (data.get('edges')  list)  ValueError(msg starting with source_path and 'expected an \'edges\' list'))  (valid JSON  data  dict  L := data['edges']  list  ( i[0,|L|-1] such that L[i]  dict)  ValueError(msg starting with f\"{source_path}:edges[{i+1}]\" and 'expected edge object'))  (valid JSON  data  dict  L := data['edges']  list  ( i[0,|L|-1], L[i]  dict)  function returns R with R = [ _edge_from_mapping(L[i], f\"{source_path}:edges[{i+1}]\") for i in range(|L|) ] and  i : (R[i].callee.fqn  \"\")  (R[i].caller.fqn  \"\"  R[i].caller.callsite_names  [])  R[i].source...

---

## Code Evidence

Line 13: if not isinstance(item, dict):
Line 14:     raise ValueError(f"{item_source}: expected edge object")
Line 15: edges.append(_edge_from_mapping(item, item_source))

---

## Trigger Condition

The code only checks that each element of the 'edges' list is a dict, but does not validate that the dict contains the required keys (e.g., 'callee' and 'caller'). If an element is an empty dict, _edge_from_mapping may raise a KeyError or return a CallEdge with empty callee.fqn, violating the specification that every returned CallEdge must have a callee with a non-empty fqn and a caller with at least one non-empty field.

---

## How to trigger the bug

The bug could not be confirmed. While `_load_json_edges` only checks `isinstance(item, dict)` on the `edges` elements, it delegates each dict element to `_edge_from_mapping`, which in turn calls `_parse_caller` and `_parse_callee`. These downstream functions thoroughly validate the dict contents: they check for the presence of `caller` and `callee` keys (raising `ValueError` if missing), validate `callee.fqn` is a non-empty string (via `_required_string`), and enforce that at least one of `caller.fqn` or `caller.callsite_names` is non-empty. Therefore, no invalid `CallEdge` can be returned by `_load_json_edges`; any malformed edge dict triggers a `ValueError` before a `CallEdge` is constructed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `text` (JSON) | `{"edges": [{}]}` (empty dict in edges array) |
| `source_path` | `"/tmp/xxx.json"` (temp file path) |

### Expected (spec-correct) Output

`ValueError` — function should reject invalid edge dicts before returning them as CallEdges

### Actual (buggy) Output

`ValueError("/tmp/xxx.json:edges[1]: missing object 'caller'")` — the empty dict was correctly caught by `_parse_caller` in the `_edge_from_mapping` chain

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
import src.call_graph_edges as cge

# Empty dict in edges array
payload = json.dumps({"edges": [{}]})
fd, path = tempfile.mkstemp(suffix='.json')
os.write(fd, payload.encode())
os.close(fd)

try:
    result = cge.load_call_edges(path)
    print(f"UNEXPECTED: returned {result}")
except ValueError as e:
    print(f"Caught ValueError: {e}")
    # actual (buggy) output: ValueError: ...edges[1]: missing object 'caller'
    # expected (correct) output: ValueError (the input is rejected)
finally:
    os.remove(path)
```

---

## Probe Script

```python
"""Probe script for bug: _load_json_edges — attempt 3: boundary cases."""
import sys
import os
import json
import tempfile

try:
    import src.call_graph_edges as cge

    # Attempt 3: test boundary cases that might bypass string validation
    test_cases = [
        ("caller_fqn_bool", [{"caller": {"fqn": True}, "callee": {"fqn": "ok"}}]),
        ("caller_fqn_list", [{"caller": {"fqn": ["a"]}, "callee": {"fqn": "ok"}}]),
        ("callee_missing_key", [{"caller": {"fqn": "x"}, "x": "y"}]),
        ("caller_all_whitespace", [{"caller": {"fqn": "  ", "callsite_names": ["  "]}, "callee": {"fqn": "ok"}}]),
        ("no_caller_key", [{"callee": {"fqn": "ok"}}]),
        ("callee_no_fqn_key", [{"caller": {"fqn": "x"}, "callee": {}}]),
    ]

    bug_confirmed = False
    trig_name = None
    trig_detail = None

    for name, edges_payload in test_cases:
        payload = {"edges": edges_payload}
        buggy_json = json.dumps(payload)

        fd, tmp_path = tempfile.mkstemp(suffix='.json')
        try:
            os.write(fd, buggy_json.encode())
            os.close(fd)

            raised_error = None
            actual_list = None

            try:
                actual_list = cge.load_call_edges(tmp_path)
            except ValueError as e:
                raised_error = str(e)
            except Exception as e:
                print(f'ERROR [{name}]: {type(e).__name__}: {e}')
                sys.exit(1)

            if actual_list is not None:
                for i, edge in enumerate(actual_list):
                    callee_empty = not edge.callee.fqn
                    caller_empty = (not edge.caller.fqn
                                    and not edge.caller.callsite_names)
                    if callee_empty or caller_empty:
                        bug_confirmed = True
                        trig_name = name
                        trig_detail = (
                            f'Invalid CallEdge[{i}]: '
                            f'callee.fqn={edge.callee.fqn!r}, '
                            f'caller.fqn={edge.caller.fqn!r}, '
                            f'caller.callsite_names={edge.caller.callsite_names!r}'
                        )
                        break
                if bug_confirmed:
                    break
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    if bug_confirmed:
        print(f'CONFIRMED — [{trig_name}]: {trig_detail} | expected: ValueError or valid CallEdge')
    else:
        print('NOT CONFIRMED — all boundary cases raised ValueError before returning invalid CallEdge')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — all boundary cases raised ValueError before returning invalid CallEdge
```
