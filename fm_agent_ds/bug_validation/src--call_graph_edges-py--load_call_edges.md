# Bug Report: load_call_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/load_call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When path is None, returns an empty list. When path identifies a single file, returns the CallEdge objects parsed from that file with all duplicate edges removed. When path identifies a directory, returns the CallEdge objects from every qualifying edge file found recursively under that directory, combined into a single list with all duplicate edges removed. In all non-None cases, each returned element is a CallEdge, and for any distinct pair of caller and callee specifications at most one CallEdge appears. Results derived from a directory walk are returned in a stable order consistent with the filesystem walk ordering.

---

### Actual Behavior

Natural language: If `path` is `None`, the return value is an empty list. Otherwise, let `p = Path(path)`. If `p` is a directory, the function recursively collects files via `p.rglob('*')`, selects those for which `is_file()` and `_is_edge_file()` return `True`, sorts them lexicographically, loads the `CallEdge` list from each via `_load_call_edge_file`, concatenates them in that order, deduplicates by caller/callee specification while preserving first occurrence, and returns the resulting list. If `p` is a file, the function loads the `CallEdge` list from that file via `_load_call_edge_file`, deduplicates it, and returns the result. If any step raises an exception (e.g., `Path` construction, filesystem traversal, file reading, or JSON parsing), that exception propagates and no value is returned.

Formal logic:
Let `ret` denote the return value after successful execution.
- If `path is None`: `ret = []`.
- Else define `p = Path(path)`.
  - If `p.is_dir()`:
    `files = [f for f in sorted(p.rglob('*')) if f.is_file() and _is_edge_file(f)]`
    `edges = concatenation of [(_load_call_edge_file(f)) for f in files]`
    `ret = dedupe(edges)` where `dedupe` ensures ` i<j, (ret[i].caller == ret[j].caller  ret[i].callee == ret[j].callee)` and each element appears at its earliest occurrence index in `edges`.
  - If `p.is_file()`:
    `ret = dedupe(_load_call_edge_file(p))`.
If any operation above raises an exception `E`, the function exits with exception `E` and `ret` is not produced.

---

## Code Evidence

Line 8:         for file_path in sorted(edge_path.rglob("*")):

---

## Trigger Condition

The specification requires the order of results to be 'consistent with the filesystem walk ordering', i.e., the order in which rglob yields the entries. The code invokes sorted() on the rglob result, which imposes an alphabetical order that may differ from the walk ordering, thereby violating the specification.

---

## How to trigger the bug

The bug is triggered by providing a directory path containing multiple edge JSON files whose names are not already in alphabetical order. The `sorted()` call reorders them alphabetically, which violates the spec requirement that results be "consistent with the filesystem walk ordering" (the order `rglob` naturally emits).

The observable effect is visible when two edge files contain edges with the same `(caller.fqn, callee.fqn)` key: the `source` field and merged `callsite_names` order depend on which file is processed first. The `sorted()` call ensures the alphabetically-first file "wins," rather than the file that `rglob` actually encounters first.

### Inputs

| Parameter | Value |
|-----------|-------|
| path | `<tempdir>` containing two JSON files: `z.json` and `a.json` |

### Expected (spec-correct) Output

The result's `source` field should reflect the file that `rglob` encounters first (walk order). On this filesystem, `rglob` returned `['z.json', 'a.json']`, so the expected source is `"SOURCE_FROM_z"`.

### Actual (buggy) Output

The result's `source` field is `"SOURCE_FROM_a"` because `sorted(rglob(...))` processes `a.json` before `z.json` alphabetically.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, json
from pathlib import Path
from src.call_graph_edges import load_call_edges

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    
    edge_z = {"edges": [{
        "caller": {"fqn": "same::caller", "callsite_names": ["from_z"]},
        "callee": {"fqn": "same::callee"},
        "source": "SOURCE_FROM_z"
    }]}
    edge_a = {"edges": [{
        "caller": {"fqn": "same::caller", "callsite_names": ["from_a"]},
        "callee": {"fqn": "same::callee"},
        "source": "SOURCE_FROM_a"
    }]}
    
    (tmp / "z.json").write_text(json.dumps(edge_z))
    (tmp / "a.json").write_text(json.dumps(edge_a))
    
    result = load_call_edges(str(tmpdir))
    print(result[0].source)
    # actual (buggy) output: SOURCE_FROM_a (sorted order)
    # expected (correct) output: SOURCE_FROM_z (walk order, on this filesystem)
```

---

## Probe Script

```python
import sys
import tempfile
import json
import os
from pathlib import Path

try:
    # Add the repo root (two dirs up from this probe script) to sys.path
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, repo_root)
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f'ERROR: Failed to import load_call_edges: {e}')
    sys.exit(1)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)

    # Create two JSON edge files with names designed to expose ordering differences.
    # Both files contain edges with the SAME (caller.fqn, callee.fqn) key so that
    # _dedupe_edges merges them and the first-processed file "wins" for the source field.
    # The source string encodes which file it came from, making the winner observable.

    edge_z = {
        "edges": [{
            "caller": {"fqn": "same::caller", "callsite_names": ["from_z"]},
            "callee": {"fqn": "same::callee"},
            "source": "SOURCE_FROM_z"
        }]
    }
    edge_a = {
        "edges": [{
            "caller": {"fqn": "same::caller", "callsite_names": ["from_a"]},
            "callee": {"fqn": "same::callee"},
            "source": "SOURCE_FROM_a"
        }]
    }

    (tmp / "z.json").write_text(json.dumps(edge_z))
    (tmp / "a.json").write_text(json.dumps(edge_a))

    # Determine the natural rglob walk order (filesystem-dependent)
    rglob_files = [p.name for p in tmp.rglob("*") if p.is_file()]
    sorted_files = sorted(rglob_files)

    print(f"rglob walk order:   {rglob_files}")
    print(f"sorted(rglob) order: {sorted_files}")

    # Call load_call_edges
    result = load_call_edges(str(tmpdir))
    if not result:
        print("ERROR: load_call_edges returned empty list")
        sys.exit(1)

    merged_edge = result[0]
    actual_source = merged_edge.source
    print(f"load_call_edges merged edge source: {actual_source!r}")

    # The spec requires results in "filesystem walk order" (rglob order).
    # If rglob processes z.json first, the spec-consistent source would be "SOURCE_FROM_z".
    # If rglob processes a.json first, the spec-consistent source would be "SOURCE_FROM_a".
    # The current code uses sorted(rglob("*")), which always processes a.json before z.json
    # (alphabetical order), so the buggy output would have source "SOURCE_FROM_a"
    # regardless of the filesystem walk order.

    # Determine expected from spec (walk order)
    first_rglob_file = rglob_files[0]
    expected_from_walk = f"SOURCE_FROM_{first_rglob_file[0]}"  # "SOURCE_FROM_z" or "SOURCE_FROM_a"

    # Determine expected from sorted (buggy behavior)
    first_sorted_file = sorted_files[0]
    expected_from_sorted = f"SOURCE_FROM_{first_sorted_file[0]}"  # always "SOURCE_FROM_a"

    # If walk order and sorted order differ, we can confirm the bug:
    # The buggy code uses sorted order, NOT walk order.
    if rglob_files != sorted_files:
        # Order differs between walk and sort — we can check which one wins
        if actual_source == expected_from_sorted:
            print(f"CONFIRMED — load_call_edges uses sorted order (source={actual_source!r}) "
                  f"instead of walk order (expected={expected_from_walk!r})")
        elif actual_source == expected_from_walk:
            print(f"NOT CONFIRMED — load_call_edges correctly uses walk order "
                  f"(source={actual_source!r})")
        else:
            print(f"NOT CONFIRMED — unexpected source value: {actual_source!r}")
    else:
        # Walk order happens to equal sorted order on this filesystem
        if actual_source == expected_from_sorted:
            print(f"NOT CONFIRMED — on this filesystem, rglob walk order "
                  f"({rglob_files}) equals sorted order "
                  f"({sorted_files}); cannot distinguish buggy from correct behavior")
        else:
            print(f"NOT CONFIRMED — unexpected source value: {actual_source!r}")
```

### Probe Output

```
rglob walk order:   ['z.json', 'a.json']
sorted(rglob) order: ['a.json', 'z.json']
load_call_edges merged edge source: 'SOURCE_FROM_a'
CONFIRMED — load_call_edges uses sorted order (source='SOURCE_FROM_a') instead of walk order (expected='SOURCE_FROM_z')
```
