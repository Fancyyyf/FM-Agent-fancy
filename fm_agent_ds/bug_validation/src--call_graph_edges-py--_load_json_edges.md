# Bug Report: _load_json_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_load_json_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The specification requires that all exceptions raised during edge parsing (specifically from `_edge_from_mapping`) be surfaced as `ValueError` with `source_path` in the message. The code at line 118 does not wrap the `_edge_from_mapping` call in a try/except block, so exceptions propagate directly. The formal verification flagged this as a potential violation: if `_edge_from_mapping` were to raise a non-`ValueError` exception (e.g., `KeyError` or `TypeError`), it would leak through without the required `ValueError` wrapping.

However, after thorough testing with 18 distinct invalid input scenarios, all code paths through `_edge_from_mapping` and its callees (`_parse_caller`, `_parse_callee`, `_required_string`, `_optional_string`, `_string_list`, `_edge_source`, `_clean_label`) consistently raise `ValueError` with the source path embedded in the error message. No non-`ValueError` exception path was found.

The formal verification is technically correct that the code does not **explicitly** wrap exceptions, but the actual runtime behavior satisfies the specification because all helper functions defensively validate inputs and raise `ValueError` themselves.

### Specification Claim

Returns a list of CallEdge objects in the same order as the elements appear in the 'edges' JSON array. Raises ValueError (with source_path included in the message) when text is not valid JSON (wrapping the underlying JSONDecodeError), when the parsed JSON is not a dict, when the 'edges' key is absent or its value is not a list, or when any element of the 'edges' array is not a dict convertible to a CallEdge.

---

### Actual Behavior

On normal return, the function returns a list `R` of `CallEdge` objects. There exists a parsed JSON value `data` such that `data = json.loads(text)` (no JSON decode error) and `isinstance(data, dict)` and `isinstance(data.get('edges'), list)` hold. `len(R) == len(data['edges'])`. For each `i` in `range(len(R))`, let `item = data['edges'][i]`; then `isinstance(item, dict)` is true, and `R[i]` is the result of `_edge_from_mapping(item, source_path + ':edges[' + str(i+1) + ']')`. If any step fails, a `ValueError` is raised: if `json.loads(text)` raises `json.JSONDecodeError`, it is wrapped as `ValueError(f'{source_path}: invalid JSON: {exc}')`; if data is not a dict, raise `ValueError(...)`; if `data.get('edges')` is not a list, raise `ValueError(...)`; if any `item` is not a dict, raise `ValueError(f'{source_path}:edges[{idx}]...')`; exceptions from `_edge_from_mapping` propagate.

---

## Code Evidence

Line 15: `edges.append(_edge_from_mapping(item, item_source))`

---

## Trigger Condition

When an element of the 'edges' array is a dict but not convertible to a CallEdge (e.g., missing required keys), _edge_from_mapping may raise a non-ValueError exception (such as KeyError or TypeError). The specification requires raising ValueError with source_path in the message for such invalid elements. The code does not intercept exceptions from _edge_from_mapping to re-raise as ValueError, violating the spec.

---

## How to trigger the bug

Despite the formal verification flagging a potential exception-wrapping gap, all 18 tested invalid input scenarios consistently raised `ValueError` with the source path in the error message. No `KeyError`, `TypeError`, or other non-`ValueError` exception was observed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `text` | JSON strings with various invalid edge structures (see test cases below) |
| `source_path` | Path to a temporary JSON file |

### Expected (spec-correct) Output

`ValueError` raised with `source_path` in the message for any invalid edge element.

### Actual (buggy) Output

`ValueError` raised with `source_path` in the message for all 18 invalid edge scenarios tested. Behavior matches the specification.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
import src.call_graph_edges as pkg

# Any of these should trigger the bug per the specification:
# Edge with callee key missing entirely
data = {"edges": [{"caller": {"fqn": "ns::func"}}]}

with tempfile.TemporaryDirectory() as tmpdir:
    fp = os.path.join(tmpdir, "test.json")
    with open(fp, "w") as f:
        json.dump(data, f)
    try:
        pkg.load_call_edges(fp)
    except ValueError as e:
        print("ValueError (spec-compliant):", e)
```
// actual (buggy) output: ValueError raised — matches specification
// expected (correct) output: ValueError raised

---

## Probe Script

```python
"""Probe script for bug: _load_json_edges doesn't wrap _edge_from_mapping exceptions.

Bug ID: src--call_graph_edges-py--_load_json_edges

Trigger condition: When an element of the 'edges' array is a dict not convertible to
a CallEdge (e.g., missing required keys), _edge_from_mapping may raise a non-ValueError
exception. The spec requires ValueError be raised.
"""
import json
import os
import sys
import tempfile

# Ensure repo root is on sys.path for package import
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Use the public entry point from the package
import src.call_graph_edges as pkg


def run_test(name: str, edge_data: dict) -> tuple[str, str | None, str | None]:
    """Run a single test case. Returns (classification, exception_type, detail)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(edge_data, f)

        try:
            actual = pkg.load_call_edges(filepath)
            return ("not_confirmed", None, f"no exception raised, returned {actual}")
        except Exception as e:
            exc_type = type(e).__name__
            if issubclass(type(e), ValueError):
                return ("not_confirmed_valueerror", exc_type, str(e))
            else:
                return ("confirmed", exc_type, str(e))


def main():
    # Test cases designed to trigger the bug:
    #   invalid edges that should raise ValueError but may raise something else.
    tests = {
        "callee_missing": {
            "edges": [{"caller": {"fqn": "ns::func"}}]
        },
        "callee_none": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": None}]
        },
        "callee_empty": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": {}}]
        },
        "callee_list": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": [1, 2, 3]}]
        },
        "caller_missing": {
            "edges": [{"callee": {"fqn": "ns::target"}}]
        },
        "caller_none": {
            "edges": [{"caller": None, "callee": {"fqn": "ns::target"}}]
        },
        "caller_empty": {
            "edges": [{"caller": {}, "callee": {"fqn": "ns::target"}}]
        },
        "callee_fqn_int": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": {"fqn": 42}}]
        },
        "callee_fqn_list": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": {"fqn": ["not", "a", "string"]}}]
        },
        "callsite_not_list": {
            "edges": [{"caller": {"callsite_names": "not_a_list"}, "callee": {"fqn": "ns::target"}}]
        },
        "info_names_not_list": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": {"fqn": "ns::target", "info_names": "not_a_list"}}]
        },
        "callee_fqn_empty": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": {"fqn": ""}}]
        },
        "callee_fqn_whitespace": {
            "edges": [{"caller": {"fqn": "ns::func"}, "callee": {"fqn": "   "}}]
        },
        "caller_fqn_none": {
            "edges": [{"caller": {"fqn": None}, "callee": {"fqn": "ns::target"}}]
        },
        "edge_item_is_list": {
            "edges": [[1, 2, 3]]
        },
        "edge_item_is_none": {
            "edges": [None]
        },
        "edge_item_is_string": {
            "edges": ["not_a_dict"]
        },
        "caller_fqn_bool": {
            "edges": [{"caller": {"fqn": True}, "callee": {"fqn": "ns::target"}}]
        },
    }

    confirmed = []
    not_confirmed = []

    for name, edge_data in tests.items():
        classification, exc_type, detail = run_test(name, edge_data)
        status_line = f"[{classification}] {name}: {detail[:120]}"
        print(status_line)
        if classification.startswith("confirmed"):
            confirmed.append((name, exc_type, detail))
        else:
            not_confirmed.append((name, exc_type, detail))

    print()
    if confirmed:
        print(f"CONFIRMED — {len(confirmed)} test(s) triggered non-ValueError:")
        for name, exc_type, detail in confirmed:
            print(f"  - {name}: {exc_type}: {detail}")
    else:
        print(f"NOT CONFIRMED — All {len(not_confirmed)} exception-raising tests"
              f" caught ValueError (spec-compliant). No non-ValueError leak found.")


if __name__ == "__main__":
    main()
```

### Probe Output

```
[not_confirmed_valueerror] callee_missing: /tmp/tmpfa9b8863/test.json:edges[1]: missing object 'callee'
[not_confirmed_valueerror] callee_none: /tmp/tmp64haur3k/test.json:edges[1]: missing object 'callee'
[not_confirmed_valueerror] callee_empty: /tmp/tmp3e3psjcm/test.json:edges[1]: missing non-empty string 'callee.fqn'
[not_confirmed_valueerror] callee_list: /tmp/tmp_4hpw0dr/test.json:edges[1]: missing object 'callee'
[not_confirmed_valueerror] caller_missing: /tmp/tmptpae51v3/test.json:edges[1]: missing object 'caller'
[not_confirmed_valueerror] caller_none: /tmp/tmpo9kd4rur/test.json:edges[1]: missing object 'caller'
[not_confirmed_valueerror] caller_empty: /tmp/tmp2h4_or7i/test.json:edges[1]: at least one of 'caller.fqn' or 'caller.callsite_names' must be non-empty
[not_confirmed_valueerror] callee_fqn_int: /tmp/tmpfkcb4r4z/test.json:edges[1]: missing non-empty string 'callee.fqn'
[not_confirmed_valueerror] callee_fqn_list: /tmp/tmp7vm6624x/test.json:edges[1]: missing non-empty string 'callee.fqn'
[not_confirmed_valueerror] callsite_not_list: /tmp/tmpmdt1861x/test.json:edges[1]: 'caller.callsite_names' must be a string array
[not_confirmed_valueerror] info_names_not_list: /tmp/tmp43d57dwu/test.json:edges[1]: 'callee.info_names' must be a string array
[not_confirmed_valueerror] callee_fqn_empty: /tmp/tmp2yry8_8p/test.json:edges[1]: missing non-empty string 'callee.fqn'
[not_confirmed_valueerror] callee_fqn_whitespace: /tmp/tmpeunil__1/test.json:edges[1]: missing non-empty string 'callee.fqn'
[not_confirmed_valueerror] caller_fqn_none: /tmp/tmpm2mmaqrc/test.json:edges[1]: at least one of 'caller.fqn' or 'caller.callsite_names' must be non-empty
[not_confirmed_valueerror] edge_item_is_list: /tmp/tmppvleltmo/test.json:edges[1]: expected edge object
[not_confirmed_valueerror] edge_item_is_none: /tmp/tmpx8kb61zt/test.json:edges[1]: expected edge object
[not_confirmed_valueerror] edge_item_is_string: /tmp/tmp5ctnbu_r/test.json:edges[1]: expected edge object
[not_confirmed_valueerror] caller_fqn_bool: /tmp/tmp4v60k7l8/test.json:edges[1]: 'caller.fqn' must be a string

NOT CONFIRMED — All 18 exception-raising tests caught ValueError (spec-compliant). No non-ValueError leak found.
```
