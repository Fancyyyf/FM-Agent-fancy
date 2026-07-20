# Bug Report: _edge_source

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/call_graph_edges-py/_edge_source.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string identifying the edge origin
  - When item contains a key \"source\" whose value is a string that is non-empty after stripping, returns that stripped string
  - When no valid \"source\" value is present and item contains a key \"evidence\" whose value is a list, returns up to 4 elements from that list, each converted to a string and stripped, joined by \"; \", provided at least one such element is non-empty after stripping
  - When no valid \"source\" value is present and item contains a key \"evidence\" whose value is a string that is non-empty after stripping, returns that stripped string
  - Otherwise, returns fallback unchanged
  - Never raises an exception

---

### Actual Behavior

The function returns a string. If the input dictionary 'item' contains a key 'source' with a value that is a string and is not empty after stripping whitespace, the function returns that stripped string. Otherwise, it checks the key 'evidence'. If the value is a list, it collects all elements that, when converted to a string and stripped, yield a non-empty string; if any such elements exist, it returns a string formed by joining the first four of them with '; '. If no such elements exist, or if 'evidence' is not a list, the function then checks if 'evidence' is a string whose stripped value is non-empty; if so, it returns that stripped string. In all other cases (missing keys, non-matching types, empty strings after stripping), it returns the provided 'fallback' string.

Formal logic:
Let r be the return value, src = item.get(\"source\"), ev = item.get(\"evidence\").
Precondition: isinstance(item, dict)  isinstance(fallback, str).
Postcondition:
  (isinstance(src, str)  src.strip()  \"\")  r = src.strip()
  
  (isinstance(src, str)  src.strip()  \"\") 
    [ (isinstance(ev, list)  ( V = [str(x).strip() for x in ev]   non-empty elements) ) ?
        (if V  [] then r = \"; \".join(V[:4])) ]
    
    ( (isinstance(ev, list)  V  [])  isinstance(ev, str)  ev.strip()  \"\"  r = ev.strip() )
    
    ( (isinstance(ev, list)  V  [])  (isinstance(ev, str)  ev.strip()  \"\")  r = fallback )
  ]

More precisely, in a case-splitting form:
  (src is str  src.strip()  \"\")  r = src.strip()
  (src is not a str  src.strip() = \"\")  (ev is list   w  ev such that str(w).strip()  \"\")  r = \"; \".join([s for s in [str(w).strip() for w in ev] if s][:4])
  (src is not a str  src.strip() = \"\")  (ev is list   w  ev with str(w).strip()  \"\")  (ev is str  ev.strip()  \"\")  r = ev.strip()
  otherwise  r = fallback

---

## Code Evidence

Line 7: values = [str(value).strip() for value in evidence if str(value).strip()]

---

## Trigger Condition

The code filters out elements that are empty after stripping, but the specification requires joining up to 4 elements (including empty ones) as long as at least one is non-empty after stripping. For the given input, the code returns 'a' while the specification expects '; a'.

---

## How to trigger the bug

The bug is in `_edge_source` (line 168 of `src/call_graph_edges.py`). When the `evidence` list contains a mix of empty and non-empty strings after stripping, the list comprehension filters out the empty elements. The specification says to keep all elements (up to 4), converting each to a string and stripping, then joining with `; `, as long as at least one element is non-empty after stripping.

### Inputs

| Parameter | Value |
|-----------|-------|
| item (evidence) | `["", "a"]` |
| item (source) | not present |
| fallback | `"test_source:edges[1]"` (set by `_edge_from_mapping`) |

### Expected (spec-correct) Output

`"; a"`

### Actual (buggy) Output

`"a"`

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
        "callee": {"fqn": "test::target_func"},
        "evidence": ["", "a"],
    }]
}

fd, tmp_path = tempfile.mkstemp(suffix=".json")
with os.fdopen(fd, "w") as f:
    json.dump(edge_data, f)

edges = load_call_edges(tmp_path)
os.unlink(tmp_path)

print(repr(edges[0].source))
# actual (buggy) output: 'a'
# expected (correct) output: '; a'
```

---

## Probe Script

```python
"""Probe script for _edge_source bug: evidence list filtering skips empty elements.

Bug: Line 168 filters out empty-after-stripping evidence elements.
For evidence=["", "a"], code returns "a", spec requires "; a".
"""
import json
import os
import sys
import tempfile

try:
    # Load via public package entry point
    from src.call_graph_edges import load_call_edges

    # Create a temporary JSON file with the trigger data
    edge_data = {
        "edges": [
            {
                "caller": {
                    "callsite_names": ["test_callsite"],
                },
                "callee": {
                    "fqn": "test::target_func",
                },
                "evidence": ["", "a"],
            }
        ]
    }

    # Write to temp file
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_edge_source_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(edge_data, f)

        # Call the public API
        edges = load_call_edges(tmp_path)
    finally:
        os.unlink(tmp_path)

    if len(edges) != 1:
        print(f"ERROR: expected 1 edge, got {len(edges)}")
        sys.exit(1)

    actual = edges[0].source
    expected = "; a"

    # Bug confirmed if actual != expected
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'a' | expected: '; a'
```
