# Bug Report: _build_call_graph

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/src/generate_topdown_layers-py/_build_call_graph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 6-tuple of dicts: (callees_map, callers_map, all_callees_map,
    file_map, module_map, edge_aliases_map), all keyed by FQN strings
  - callees_map[fqn]: set of FQNs called by fqn within the same phase; every
    callee FQN corresponds to an extracted function and is never equal to fqn
  - callers_map[fqn]: set of FQNs from the same phase that call fqn; every
    caller FQN is a member of the phase's FQN set
  - all_callees_map[fqn]: set of FQNs called by fqn across all phases  a
    superset of callees_map[fqn]; when global_stem_to_fqns is None, this set
    contains only within-phase callees; when provided, it may include FQNs
    from other phases
  - file_map[fqn]: absolute path to the extracted function file for fqn
  - module_map[fqn]: module name string from phases.json for fqn
  - edge_aliases_map[callee_fqn][caller_fqn]: set of supplemental info names
    for the edge from caller_fqn to callee_fqn, derived from extra_call_edges
    and static analysis; absent entry implies the empty set
  - Callee resolution uses the codegraph backend when available for the file's
    language; otherwise falls back to regex-based bare-name call-site detection
    where each detected stem resolves to every FQN mapping to that stem (an
    over-approximation that only includes extracted-function targets)
  - Extra call edges from extra_call_edges are merged into the returned maps
    for callers matched by exact FQN or by callsite name detected in source
  - If a source file cannot be opened for reading, no callee edges are added
    for that file and it is silently skipped

---

### Actual Behavior

The function returns the tuple (callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map). No exceptions propagate out of the block; all OSError exceptions from file reading are caught and result in an empty text string or a `continue`. The input arguments are not mutated.

In the codegraph path (lang_key in registry_langs), `callee_fqns` is computed from `registry_edges` on lines 323-324 *before* any attempt to open the source file. The file-open block on lines 327-334 only guards `called_stems` (extra-edge call-site detection), not `callee_fqns`. When the file cannot be opened, an OSError is silently caught (text = "") and `called_stems` is computed from that empty text, but `callee_fqns` — already populated from `registry_edges` — still contains codegraph-resolved callee FQNs. These edges are then unconditionally added to `callees_map`, `callers_map`, and `all_callees_map` in the loop at lines 348-352.

This directly violates the spec requirement: "If a source file cannot be opened for reading, no callee edges are added for that file and it is silently skipped."

By contrast, the regex fallback path (the `else` branch at lines 335-346) correctly uses `continue` when the file cannot be opened, fully skipping edge addition for that file.

---

## Code Evidence

Line 63: callee_fqns = {c for c in registry_edges.get(fqn, set())
Line 64:                if c != fqn and c in known_fqns}

(Lines 323-324 in `src/generate_topdown_layers.py`.)

---

## Trigger Condition

Specification B states that if a source file cannot be opened for reading, no callee edges are added for that file and it is silently skipped. In the codegraph path (lang_key in registry_langs), the code still adds callee edges from registry_edges even when the file open fails, which violates this requirement.

---

## How to trigger the bug

When `_build_call_graph` processes a source file whose language is handled by the codegraph backend (`lang_key in registry_langs`), any codegraph-resolved edges for that file's FQN are added to the output maps unconditionally. The file-open attempt only guards the extra-edge call-site scan (`_find_call_sites` for `extra_edges_by_callsite`), not the codegraph-derived `callee_fqns`. If the file is unreadable (e.g., permissions removed), edges from `registry_edges` are still added.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phase_files` | List containing two `(filepath, module_name)` tuples: a caller file (unreadable) and a callee file (readable), both using a codegraph-handled language (`.c`) |
| `proj_dir` | Temporary project directory containing `extracted_functions/` with the test files |
| `global_stem_to_fqns` | `None` |
| `extra_call_edges` | `None` |
| Mocked `call_edges_all` | Returns `({caller_fqn: {callee_fqn}}, {"c"})` — simulates codegraph having resolved an edge |

### Expected (spec-correct) Output

`callees_map` and `all_callees_map` should contain **no entries** for the unreadable caller FQN. The spec requires that when a source file cannot be opened, it is silently skipped — no callee edges are added.

### Actual (buggy) Output

`callees_map[caller_fqn]` contains `{callee_fqn}` and `all_callees_map[caller_fqn]` contains `{callee_fqn}`, despite the caller's source file being unreadable (permissions 000). The codegraph-derived edges are added because `callee_fqns` is computed from `registry_edges` before the file-open check.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from unittest.mock import patch
from src.generate_topdown_layers import _build_call_graph, _file_to_fqn

with tempfile.TemporaryDirectory() as proj_dir:
    extracted_dir = os.path.join(proj_dir, "extracted_functions", "src", "test-c")
    os.makedirs(extracted_dir)

    caller_path = os.path.join(extracted_dir, "caller_func.c")
    callee_path = os.path.join(extracted_dir, "callee_func.c")
    for path in (caller_path, callee_path):
        with open(path, "w") as f:
            f.write("// test file\n")

    caller_fqn = _file_to_fqn(caller_path, proj_dir)
    callee_fqn = _file_to_fqn(callee_path, proj_dir)

    os.chmod(caller_path, 0o000)  # make unreadable

    mock_edges = {caller_fqn: {callee_fqn}}
    mock_langs = {"c"}

    with patch("src.generate_topdown_layers.call_edges_all",
               return_value=(mock_edges, mock_langs)):
        callees_map, _, all_callees_map, _, _, _ = _build_call_graph(
            [(caller_path, "test_module"), (callee_path, "callee_module")], proj_dir
        )

    # actual (buggy) output: callees_map[caller_fqn] = {callee_fqn}
    # expected (correct) output: callees_map[caller_fqn] = set()  (no edges)

    print(f"callees_map for unreadable caller: {sorted(callees_map.get(caller_fqn, set()))}")
    print(f"all_callees_map for unreadable caller: {sorted(all_callees_map.get(caller_fqn, set()))}")
```

---

## Probe Script

```python
"""Probe script: verify _build_call_graph adds codegraph callee edges even when
the source file cannot be opened for reading.

Spec claim: If a source file cannot be opened for reading, no callee edges are
            added for that file and it is silently skipped.
Bug: In the codegraph path (lang_key in registry_langs), callee_fqns is computed
     from registry_edges *before* any file-open attempt. When the file is
     unreadable and no extra edges are configured, the file-open block is
     skipped entirely, yet codegraph-derived edges are still added to
     callees_map and all_callees_map — violating the spec.
"""

import sys
import os
import tempfile
from unittest.mock import patch

# Add repo root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.generate_topdown_layers import _build_call_graph, _file_to_fqn

    with tempfile.TemporaryDirectory() as proj_dir:
        # Set up the extracted_functions directory structure
        extracted_dir = os.path.join(proj_dir, "extracted_functions", "src", "test-c")
        os.makedirs(extracted_dir)

        # Create two function files:
        #  - caller_func.c: the caller (will be made unreadable)
        #  - callee_func.c: the callee (stays readable for FQN mapping)
        caller_path = os.path.join(extracted_dir, "caller_func.c")
        callee_path = os.path.join(extracted_dir, "callee_func.c")

        for path in (caller_path, callee_path):
            with open(path, "w") as f:
                f.write("// test file\n")

        # Compute FQNs (pure path computation, does not read file contents)
        caller_fqn = _file_to_fqn(caller_path, proj_dir)
        callee_fqn = _file_to_fqn(callee_path, proj_dir)

        # phase_files: both files belong to the same module
        phase_files = [
            (caller_path, "test_module"),
            (callee_path, "callee_module"),
        ]

        # Make the caller file unreadable to trigger the spec condition
        os.chmod(caller_path, 0o000)

        # Mock call_edges_all: returns a codegraph edge caller_fqn -> callee_fqn
        # and registers "c" as a codegraph-handled language. This simulates the
        # scenario where codegraph has resolved the edge and the caller's source
        # file happens to be unreadable at the time _build_call_graph runs.
        mock_edges = {caller_fqn: {callee_fqn}}
        mock_langs = {"c"}

        try:
            with patch(
                "src.generate_topdown_layers.call_edges_all",
                return_value=(mock_edges, mock_langs),
            ):
                (
                    callees_map,
                    callers_map,
                    all_callees_map,
                    file_map,
                    module_map,
                    edge_aliases_map,
                ) = _build_call_graph(phase_files, proj_dir)
        finally:
            # Restore permissions so TemporaryDirectory can clean up
            os.chmod(caller_path, 0o644)

        # Check: did the unreadable caller get callee edges?
        has_callee_edges = callee_fqn in callees_map.get(caller_fqn, set())
        has_all_callee_edges = callee_fqn in all_callees_map.get(caller_fqn, set())
        bug_reproduced = has_callee_edges and has_all_callee_edges

        if bug_reproduced:
            print("CONFIRMED")
            print(f"  caller_fqn:           {caller_fqn}")
            print(f"  callee_fqn:           {callee_fqn}")
            print(f"  callees_map[caller]:  {sorted(callees_map.get(caller_fqn, set()))}")
            print(f"  all_callees_map[caller]: {sorted(all_callees_map.get(caller_fqn, set()))}")
            print(f"  spec requires: no callee edges when file cannot be opened for reading")
            print(f"  bug: codegraph-derived edges added despite unreadable source file")
        else:
            print("NOT CONFIRMED")
            print(f"  callees_map[caller]:   {sorted(callees_map.get(caller_fqn, set()))}")
            print(f"  all_callees_map[caller]: {sorted(all_callees_map.get(caller_fqn, set()))}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED
  caller_fqn:           src::test-c::caller_func
  callee_fqn:           src::test-c::callee_func
  callees_map[caller]:  ['src::test-c::callee_func']
  all_callees_map[caller]: ['src::test-c::callee_func']
  spec requires: no callee edges when file cannot be opened for reading
  bug: codegraph-derived edges added despite unreadable source file
```
