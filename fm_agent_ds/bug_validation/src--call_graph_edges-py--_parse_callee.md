# Bug Report: _parse_callee

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_parse_callee.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When value is a dict, returns a CalleeTarget whose fqn is a required non-empty string from the dict and whose info_names is a tuple of string names from the dict (defaulting to an empty tuple when the corresponding field is absent or empty). When value is not a dict, raises ValueError with a message that includes source.

---

### Actual Behavior

Post-condition (natural language): The function either raises a ValueError (with a message containing source and describing a missing or invalid 'callee' specification) or returns a CalleeTarget object. A ValueError is raised if `value` is not a dict; if `value` is a dict but `value['fqn']` is missing, None, empty, or not a string; or if `value['info_names']` exists and is not a list or contains any element that is not a string. If no ValueError is raised, `value` is a dict, `value['fqn']` is a non-empty string, and `value.get('info_names', [])` is either an empty list, a non-list (treated as empty), or a list of strings, and the function returns `CalleeTarget(fqn=value['fqn'], info_names=tuple(value.get('info_names', [])))`.

Formal logic: 
( isinstance(value, dict) 
   (let raw_fqn = value.get('fqn') in raw_fqn is non-empty string) 
   (let raw_info = value.get('info_names', []) in raw_info is empty or a list of strings) )
  (result = CalleeTarget(fqn=raw_fqn, info_names=tuple(raw_info)))

( isinstance(value, dict)  (raise ValueError(f"{source}: missing object 'callee'")) )

( isinstance(value, dict) 
   (let raw_fqn = value.get('fqn') in raw_fqn is None  raw_fqn is empty  isinstance(raw_fqn, str)) 
   (raise ValueError whose message contains source and 'callee.fqn') )

( isinstance(value, dict) 
   (let raw_fqn = value.get('fqn') in raw_fqn is non-empty string) 
   (let raw_info = value.get('info_names', []) in raw_info is not a list or contains a non-string element) 
   (raise ValueError whose message contains source and 'callee.info_names') )

---

## Code Evidence

Line 5:     info_names = _string_list(value.get("info_names", []), "callee.info_names", source)

---

## Trigger Condition

The specification requires that if the 'info_names' field is present, the function must produce a tuple of string names from that field. For an integer value like 123, the code silently treats it as an empty tuple and returns a CalleeTarget, ignoring the invalid field. The specification expects that such invalid input should be rejected (e.g., raise an error) because it cannot yield a tuple of string names.

---

## How to trigger the bug

The trigger condition describes a scenario where `callee.info_names` is an integer (e.g., 123) and the code supposedly silently treats it as an empty tuple. However, upon testing, the code **correctly raises a ValueError** for non-list `info_names` values. The `_string_list` helper function (line 190-200 of `src/call_graph_edges.py`) explicitly checks `not isinstance(value, list)` and raises a `ValueError` with the message `'{key}' must be a string array`. This means non-list values (integers, dicts, strings) are properly rejected, not silently treated as empty.

### Inputs

| Parameter | Value |
|-----------|-------|
| `value` (callee object) | `{"fqn": "target::func", "info_names": 123}` |

### Expected (spec-correct) Output

`ValueError` is raised because `info_names=123` is an integer, not a list of strings.

### Actual (buggy) Output

`ValueError: /tmp/....json:edges[1]: 'callee.info_names' must be a string array`

The actual output matches the expected (spec-correct) output. The code rejects invalid `info_names` types, contrary to the trigger condition's claim.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
from src.call_graph_edges import load_call_edges

edge_json = {
    "edges": [
        {
            "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
            "callee": {"fqn": "target::func", "info_names": 123},
        }
    ]
}

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(edge_json, f)
    tmp_path = f.name

try:
    edges = load_call_edges(tmp_path)
    print(f"Returned: {edges}")  # This would indicate a bug
except ValueError as e:
    print(f"ValueError raised: {e}")  # Expected (correct) behavior
# actual (buggy) output: ValueError raised (correct per spec)
# expected (correct) output: ValueError raised
finally:
    os.unlink(tmp_path)
```

---

## Probe Script

```python
"""Probe for bug ID: src--call_graph_edges-py--_parse_callee

Trigger condition: When value is a dict with info_names as an integer (e.g., 123),
the code should NOT silently return a CalleeTarget (treating it as empty tuple).
The spec requires that invalid info_names should be rejected (raise an error).
"""

import os
import sys
import tempfile
import json

# Ensure workspace root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.call_graph_edges import load_call_edges


def test_int_info_names():
    """
    Test: callee.info_names is an integer (123).
    Expected (spec-correct): raise an error because 123 cannot yield a tuple of string names.
    Buggy claim: code silently treats it as empty tuple and returns CalleeTarget.
    """
    edge_json = {
        "edges": [
            {
                "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
                "callee": {"fqn": "target::func", "info_names": 123},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(edge_json, f)
        tmp_path = f.name

    try:
        edges = load_call_edges(tmp_path)
        # If we get here, no error was raised — the bug claim might be confirmed
        if len(edges) > 0:
            info_names = edges[0].callee.info_names
            print(
                f"CONFIRMED — silently returned CalleeTarget with info_names={info_names!r}"
            )
        else:
            print(
                "CONFIRMED — silently returned empty result (treated as empty tuple)"
            )
    except ValueError as e:
        # ValueError raised — correct behavior per spec
        print(f"NOT CONFIRMED — actual matched expected: ValueError raised: {e}")
    except Exception as e:
        print(f"NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_list_with_int_item():
    """
    Test: callee.info_names is a list containing an integer ["foo", 123].
    Expected (spec-correct): raise an error because 123 is not a string.
    Buggy claim: code might silently skip non-string items.
    """
    edge_json = {
        "edges": [
            {
                "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
                "callee": {"fqn": "target::func", "info_names": ["foo", 123]},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(edge_json, f)
        tmp_path = f.name

    try:
        edges = load_call_edges(tmp_path)
        if len(edges) > 0:
            info_names = edges[0].callee.info_names
            print(
                f"CONFIRMED — silently returned CalleeTarget with info_names={info_names!r}"
            )
        else:
            print("CONFIRMED — silently returned empty result")
    except ValueError as e:
        print(f"NOT CONFIRMED — actual matched expected: ValueError raised: {e}")
    except Exception as e:
        print(f"NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_dict_info_names():
    """
    Test: callee.info_names is a dict like {"a": 1}.
    Expected (spec-correct): raise an error because dict is not a list of strings.
    Buggy claim: code might silently treat it as empty tuple.
    """
    edge_json = {
        "edges": [
            {
                "caller": {"fqn": "test::func", "callsite_names": ["test_call"]},
                "callee": {"fqn": "target::func", "info_names": {"a": 1}},
            }
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(edge_json, f)
        tmp_path = f.name

    try:
        edges = load_call_edges(tmp_path)
        if len(edges) > 0:
            info_names = edges[0].callee.info_names
            print(
                f"CONFIRMED — silently returned CalleeTarget with info_names={info_names!r}"
            )
        else:
            print("CONFIRMED — silently returned empty result")
    except ValueError as e:
        print(f"NOT CONFIRMED — actual matched expected: ValueError raised: {e}")
    except Exception as e:
        print(f"NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


if __name__ == "__main__":
    test_int_info_names()
    test_list_with_int_item()
    test_dict_info_names()
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: ValueError raised: /tmp/tmpxxxxx.json:edges[1]: 'callee.info_names' must be a string array
NOT CONFIRMED — actual matched expected: ValueError raised: /tmp/tmpxxxxx.json:edges[1]: callee.info_names[2] must be a string
NOT CONFIRMED — actual matched expected: ValueError raised: /tmp/tmpxxxxx.json:edges[1]: 'callee.info_names' must be a string array
```
