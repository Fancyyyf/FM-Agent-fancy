# Bug Report: _project_call_graph

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map)
  - callees_map is a dict mapping every FQN that appears in any phase of phases.json
    to the set of FQNs it directly calls, spanning all phases and including any
    supplemental edges from extra_call_edges
  - callers_map is a dict mapping every FQN to the set of FQNs that directly call it 
    the exact inverse of callees_map (FQN A  callees_map[B]  B  callers_map[A])
  - file_map is a dict mapping every FQN to the absolute filesystem path of the
    extracted-function file that defines it
  - edge_aliases_map maps callee FQN  caller FQN  supplemental edge labels as
    provided by extra_call_edges; for FQN pairs without supplemental labels the
    inner mapping is absent or empty
  - Each distinct extracted-function file path contributes its functions exactly once,
    regardless of how many phases reference that file (deduplication across phases)
  - All four returned mappings are derived from the same underlying call-graph
    computation: callees_map, callers_map, and file_map are mutually consistent
    (every FQN key in any of them appears in all of them)

---

### Actual Behavior

If the function returns, it returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map) such that: (1) callees_map is a dict mapping each fully qualified function name (FQN) extracted from any phase in the project to a set of FQNs it directly calls; (2) callers_map is the inverse mapping each FQN to the set of FQNs that directly call it; (3) file_map maps each FQN to the absolute path of its extracted-function file; (4) edge_aliases_map maps callee FQN to a dict that maps caller FQN to supplemental edge labels (from extra_call_edges). These four maps are exactly the 1st, 2nd, 4th, and 6th elements of the 6-tuple returned by _build_call_graph when applied to the unique (by file path) list of (absolute file path, module name) pairs produced by iterating over all phases in phases.json (via _load_phases and _collect_phase_files). If extra_call_edges is not None, its supplementary edges are reflected in callees_map, callers_map, and edge_aliases_map. If any internal call raises an exception, the exception propagates and no return value is produced. Formal logic: Let (callees_map, callers_map, file_map, edge_aliases_map) = _project_call_graph(work_dir, extra_call_edges). Then: phases = _load_phases(work_dir)['phases']; S = {(f, m) |  p  phases : (f, m)  _collect_phase_files(work_dir, p)}; let A be a list containing each distinct pair from S such that no two pairs share the same f; there exists a 6-tuple (callees_map0, callers_map0, _, file_map0, _, edge_aliases_map0) = _build_call_graph(A, work_dir, extra_call_edges) with callees_map0 = callees_map, callers_map0 = callers_map, file_map0 = file_map, edge_aliases_map0 = edge_aliases_map.

---

## Code Evidence

Line 19: ( ... Line 27: ) = _build_call_graph( ... Line 30: )

---

## Trigger Condition

The code unconditionally passes all_files to _build_call_graph even when the list is empty (no phases or no files from any phase). The pre-condition of _build_call_graph requires a non-empty all_files list. When all_files is empty, the call violates this contract and likely raises an exception or behaves unexpectedly, failing to return the expected 4-tuple of (possibly empty) mappings. The specification requires returning a valid 4-tuple for any valid input, including projects with no functions.

---

## How to trigger the bug

The probe attempted to reproduce the bug by calling `_project_call_graph` with a work directory whose `phases.json` has an empty phases list, and by calling `_build_call_graph` directly with an empty `phase_files` list. In both cases, the functions handled empty input gracefully without exceptions.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | `<tmpdir>/fm_agent` (empty phases.json) |
| extra_call_edges | None |

### Expected (spec-correct) Output

`({}, {}, {}, {})` — a 4-tuple of empty mappings

### Actual (buggy) Output

`({}, {}, {}, {})` — a 4-tuple of empty mappings (identical to expected)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, json, os, shutil
from src.incremental_reasoner import _project_call_graph

tmp = tempfile.mkdtemp()
try:
    wd = os.path.join(tmp, "fm_agent")
    os.makedirs(os.path.join(wd, "extracted_functions"), exist_ok=True)
    os.makedirs(os.path.join(wd, "spec_prompts"), exist_ok=True)
    with open(os.path.join(wd, "phases.json"), "w") as f:
        json.dump({"phases": []}, f)
    result = _project_call_graph(wd)
    # actual (buggy) output: ({}, {}, {}, {})
    # expected (correct) output: ({}, {}, {}, {})
    # Bug NOT confirmed — function handles empty input correctly
finally:
    shutil.rmtree(tmp)
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# ── Attempt 3: directly test _build_call_graph with empty phase_files ─────
# and also test the full _project_call_graph path with various empty scenarios

try:
    from src.generate_topdown_layers import _build_call_graph
    from src.incremental_reasoner import _project_call_graph
except ImportError as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

probe_tmp = tempfile.mkdtemp(prefix="fm_agent_probe_empty3_")
try:
    # ── Test 1: _build_call_graph directly with empty list ─────────────────
    try:
        result = _build_call_graph([], probe_tmp, global_stem_to_fqns=None, extra_call_edges=None)
    except Exception as e:
        print(
            f"CONFIRMED -- _build_call_graph([], ...) raised exception:"
            f" {type(e).__name__}: {e}"
            f" | _project_call_graph passes empty all_files here without guard"
        )
        sys.exit(0)

    # Check the return type
    if not isinstance(result, tuple) or len(result) != 6:
        print(
            f"CONFIRMED -- _build_call_graph([], ...) returned invalid result:"
            f" {type(result).__name__}"
            f" | expected: 6-tuple"
        )
        sys.exit(0)

    callees_map, callers_map, all_callees, file_map, module_map, edge_aliases_map = result

    # All six maps should be dict-like and empty
    map_checks = {
        "callees_map": (callees_map, len(callees_map) if isinstance(callees_map, dict) else -1),
        "callers_map": (callers_map, len(callers_map) if isinstance(callers_map, dict) else -1),
        "file_map": (file_map, len(file_map) if isinstance(file_map, dict) else -1),
        "module_map": (module_map, len(module_map) if isinstance(module_map, dict) else -1),
        "edge_aliases_map": (edge_aliases_map, len(edge_aliases_map) if isinstance(edge_aliases_map, dict) else -1),
    }

    unexpected = []
    for name, (val, length) in map_checks.items():
        if length < 0:
            unexpected.append(f"{name} is {type(val).__name__} not dict")
        elif length > 0:
            unexpected.append(f"{name} has {length} entries (expected 0)")

    if unexpected:
        print(f"CONFIRMED -- _build_call_graph([], ...) behaved unexpectedly: {'; '.join(unexpected)}")
        sys.exit(0)

    # ── Test 2: _project_call_graph with empty phases ──
    work_dir = os.path.join(probe_tmp, "fm_agent")
    os.makedirs(os.path.join(work_dir, "extracted_functions"), exist_ok=True)
    os.makedirs(os.path.join(work_dir, "spec_prompts"), exist_ok=True)
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump({"phases": []}, f)

    try:
        callees_map, callers_map, file_map, edge_aliases_map = _project_call_graph(
            work_dir, extra_call_edges=None
        )
    except Exception as e:
        print(
            f"CONFIRMED -- _project_call_graph raised exception with empty phases:"
            f" {type(e).__name__}: {e}"
        )
        sys.exit(0)

    maps_ok = (
        isinstance(callees_map, dict) and len(callees_map) == 0
        and isinstance(callers_map, dict) and len(callers_map) == 0
        and isinstance(file_map, dict) and len(file_map) == 0
        and isinstance(edge_aliases_map, dict)
    )

    if maps_ok:
        print(
            "NOT CONFIRMED"
            " -- _build_call_graph([], ...) returns valid empty 6-tuple;"
            " _project_call_graph with empty phases returns valid empty 4-tuple;"
            " the implementation handles empty all_files gracefully without errors."
            " The spec-generated pre-condition for _build_call_graph (non-empty all_files)"
            " does not match the actual implementation which tolerates empty input."
        )
    else:
        print(
            f"CONFIRMED -- _project_call_graph result maps are not valid/empty:"
            f" callees_map type={type(callees_map).__name__} len={len(callees_map) if isinstance(callees_map, dict) else 'N/A'},"
            f" callers_map type={type(callers_map).__name__} len={len(callers_map) if isinstance(callers_map, dict) else 'N/A'},"
            f" file_map type={type(file_map).__name__} len={len(file_map) if isinstance(file_map, dict) else 'N/A'}"
        )

finally:
    shutil.rmtree(probe_tmp, ignore_errors=True)
```

### Probe Output

```
NOT CONFIRMED -- _build_call_graph([], ...) returns valid empty 6-tuple; _project_call_graph with empty phases returns valid empty 4-tuple; the implementation handles empty all_files gracefully without errors. The spec-generated pre-condition for _build_call_graph (non-empty all_files) does not match the actual implementation which tolerates empty input.
```
