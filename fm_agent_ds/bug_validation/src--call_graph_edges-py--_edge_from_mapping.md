# Bug Report: _edge_from_mapping

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_edge_from_mapping.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a CallEdge whose caller field is a CallerSelector derived from item['caller'], whose callee field is a CalleeTarget derived from item['callee'], and whose source field is a provenance string derived from evidence entries in item combined with the provided source parameter. Raises an error whose message includes source when item is missing required sub-objects or when a sub-object is malformed.

---

### Actual Behavior

If the pre-condition holds, the function returns a CallEdge instance whose 'caller' is the CallerSelector obtained by parsing item['caller'] with _parse_caller, whose 'callee' is the CalleeTarget obtained by parsing item['callee'] with _parse_callee, and whose 'source' is the provenance string returned by _edge_source(item, source). No exceptions are raised. Formally:  item, source satisfying Pre  ( e  CallEdge (e.caller = _parse_caller(item['caller'], source)  e.callee = _parse_callee(item['callee'], source)  e.source = _edge_source(item, source)  _edge_from_mapping(item, source) returns e  no exception is raised)).

---

## Code Evidence

Line 2: caller = _parse_caller(item.get('caller'), source)
Line 3: callee = _parse_callee(item.get('callee'), source)

---

## Trigger Condition

The function does not validate that item['caller'] and item['callee'] are dicts or None before passing them to _parse_caller and _parse_callee. If a sub-object is of an incorrect type (e.g., a string), the helper functions' behavior is unspecified; they might not raise an error, or might raise an error without the source string, violating the requirement that a malformed sub-object raises an error whose message includes source.

---

## How to trigger the bug

The trigger condition claims that `_parse_caller` and `_parse_callee` have "unspecified" behavior when given non-dict values. However, both helper functions contain explicit type checks (`isinstance(value, dict)`) and raise `ValueError` with the source string in the error message. Six test cases were run through the public API (`load_call_edges`) with malformed caller/callee sub-objects (string, missing key, list), and all six raised `ValueError` with the source path in the message. The specification requirement — "Raises an error whose message includes source when item is missing required sub-objects or when a sub-object is malformed" — is fully satisfied by the delegated validation in the helper functions.

### Inputs

| Parameter | Value |
|-----------|-------|
| item (caller-as-string) | `{"caller": "not-a-dict", "callee": {"fqn": "some_func"}}` |
| item (callee-as-string) | `{"caller": {"fqn": "some_func"}, "callee": "not-a-dict"}` |
| item (caller-missing) | `{"callee": {"fqn": "some_func"}}` |
| item (callee-missing) | `{"caller": {"fqn": "some_func"}}` |
| item (caller-as-list) | `{"caller": [1, 2, 3], "callee": {"fqn": "some_func"}}` |
| item (callee-as-list) | `{"caller": {"fqn": "some_func"}, "callee": [1, 2, 3]}` |

### Expected (spec-correct) Output

`ValueError` raised with the source file path in the error message.

### Actual (buggy) Output

`ValueError` raised with the source file path in the error message (matches expected).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.call_graph_edges import load_call_edges

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "test.json")
    data = {"edges": [{"caller": "not-a-dict", "callee": {"fqn": "some_func"}}]}
    with open(path, "w") as f:
        json.dump(data, f)
    try:
        load_call_edges(path)
    except ValueError as e:
        print(f"Error: {e}")
        # actual (buggy) output: ValueError with source path included
        # expected (correct) output: ValueError with source path included
```

---

## Probe Script

```python
"""Probe for _edge_from_mapping bug: test whether malformed caller/callee
sub-objects raise errors with source path included, as the spec requires."""

import json
import sys
import tempfile
import os
from pathlib import Path

# This is the "public entry point" for the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.call_graph_edges import load_call_edges


def make_temp_json(data, tmpdir):
    """Create a temp JSON file with the given data."""
    path = os.path.join(tmpdir, "test_edges.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def run_test(label, edges, should_raise=True):
    """Run a single test case through load_call_edges."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = make_temp_json({"edges": edges}, tmpdir)
        try:
            result = load_call_edges(path)
            if should_raise:
                return False, f"{label}: expected error but got result {result}"
            return True, None
        except ValueError as e:
            if not should_raise:
                return False, f"{label}: unexpected error: {e}"
            msg = str(e)
            if path not in msg:
                return False, f"{label}: source path '{path}' not in error message: {msg}"
            return True, None
        except Exception as e:
            return False, f"{label}: unexpected exception type {type(e).__name__}: {e}"


def main():
    results = []
    source_file = "test_edges.json"

    # Test 1: caller is a string (not dict) — should raise with source
    ok, err = run_test(
        "caller-as-string",
        [{"caller": "not-a-dict", "callee": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "caller-as-string: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 2: callee is a string (not dict) — should raise with source
    ok, err = run_test(
        "callee-as-string",
        [{"caller": {"fqn": "some_func"}, "callee": "not-a-dict"}],
    )
    if ok:
        results.append(("PASS", "callee-as-string: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 3: caller key missing entirely — should raise with source
    ok, err = run_test(
        "caller-missing-key",
        [{"callee": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "caller-missing-key: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 4: callee key missing entirely — should raise with source
    ok, err = run_test(
        "callee-missing-key",
        [{"caller": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "callee-missing-key: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 5: caller is a list (not dict) — should raise with source
    ok, err = run_test(
        "caller-as-list",
        [{"caller": [1, 2, 3], "callee": {"fqn": "some_func"}}],
    )
    if ok:
        results.append(("PASS", "caller-as-list: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Test 6: callee is a list (not dict) — should raise with source
    ok, err = run_test(
        "callee-as-list",
        [{"caller": {"fqn": "some_func"}, "callee": [1, 2, 3]}],
    )
    if ok:
        results.append(("PASS", "callee-as-list: raised error with source path ✓"))
    else:
        results.append(("FAIL", err))

    # Print results
    all_passed = all(status == "PASS" for status, _msg in results)
    for status, msg in results:
        print(f"[{status}] {msg}")

    if all_passed:
        print("NOT CONFIRMED — all malformed sub-object cases raised ValueError with source path in message, matching the spec")
    else:
        print("CONFIRMED — at least one malformed sub-object case did not raise error with source path")


if __name__ == "__main__":
    main()
```

### Probe Output

```
[PASS] caller-as-string: raised error with source path ✓
[PASS] callee-as-string: raised error with source path ✓
[PASS] caller-missing-key: raised error with source path ✓
[PASS] callee-missing-key: raised error with source path ✓
[PASS] caller-as-list: raised error with source path ✓
[PASS] callee-as-list: raised error with source path ✓
NOT CONFIRMED — all malformed sub-object cases raised ValueError with source path in message, matching the spec
```
