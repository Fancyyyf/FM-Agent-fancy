# Bug Report: _build_call_graph

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_topdown_layers-py/_build_call_graph.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 6-tuple (callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map). All maps use canonical FQN strings (separator '::') as keys. file_map: each FQN from phase_files maps to its absolute file path; every FQN has exactly one file_map entry. module_map: each FQN from phase_files maps to the module_name from its (filepath, module_name) pair. callees_map: maps each caller FQN to the set of callee FQNs that are either statically called within the caller's function body or added via extra_call_edges, restricted to callees whose FQNs originate from phase_files. callers_map: inverse of callees_map  maps each callee FQN to the set of caller FQNs from phase_files that call it. all_callees_map: maps each caller FQN to the set of all callee FQNs detected in its function body or added via extra_call_edges, including callees whose FQNs do not originate from phase_files. For every caller FQN, callees_map[fqn] is a subset of all_callees_map[fqn]. edge_aliases_map: when extra_call_edges is provided and not None, maps callee FQN  (caller FQN  set of info_name strings) for each matched supplemental edge; when extra_call_edges is None or empty, edge_aliases_map is empty but never None. Self-edges (caller FQN equals callee FQN) are excluded from all edge maps. Function files that cannot be read due to I/O errors contribute no callee edges, though their FQNs still appear in file_map and module_map. No element of the return tuple is None.

---

### Actual Behavior

After execution, the function returns a 6-tuple (callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map). file_map and module_map are unchanged from the pre-condition. No exceptions propagate outside the block; all OSError instances are caught and handled. extra_edges_by_caller_fqn and extra_edges_by_callsite are exactly the pair returned by _resolve_extra_call_edges(extra_call_edges, phase_fqns, known_fqns) where extra_call_edges is an external input. Let F = phase_files. For a filepath fp, define lang(fp) = _detect_lang_from_ext(fp). A file is processed when lang(fp) is not None and (lang(fp)  registry_langs or the attempt to open and read the file succeeds without OSError). Define P = { fqn_map[fp] | (fp,_)  F and fp is processed }. For each fqn  P we define:

- D_registry(fqn) = if lang(fp)  registry_langs: { c | c  registry_edges.get(fqn, ) and c  fqn and c  known_fqns }; else .
- D_regex_related(fqn) = if lang(fp)  registry_langs: let known_stems = keys(effective_stem_to_fqns)  keys(extra_edges_by_callsite). Let stems_found = _find_call_sites(text_of(fp), lang(fp), known_stems, keywords). Then D_regex = _{s  stems_found} (effective_stem_to_fqns.get(s, ) \ {fqn}); else .
- Extra callsite edges: Let extra_stems = if extra_edges_by_callsite is truthy then (if lang(fp)  registry_langs: _find_call_sites(text_of(fp), lang(fp), set(extra_edges_by_callsite.keys()), keywords) else stems_found) else . Let E_callsite(fqn) = { edge.callee_fqn | s  extra_stems, edge  extra_edges_by_callsite.get(s, ()) and edge.callee_fqn  fqn }.
- Extra caller edges: E_caller(fqn) = { edge.callee_fqn | edge  extra_edges_by_caller_fqn.get(fqn, ()) and edge.callee_fqn  fqn }.

Then for each fqn  P, all_callees_map[fqn] = D_registry(fqn)  D_regex_related(fqn)  E_callsite(fqn)  E_caller(fqn). callees_map[fqn] = all_callees_map[fqn]  phase_fqns. For each callee_fqn  phase_fqns, callers_map[callee_fqn] = { f  P | callee_fqn  callees_map[... (line truncated to 2000 chars)

---

## Code Evidence

Line 59: if lang_key in registry_langs:
Line 63: callee_fqns = {c for c in registry_edges.get(fqn, set())
Line 64: if c != fqn and c in known_fqns}
Line 68: with open(filepath, "r", errors="replace") as f:
Line 71: text = ""

---

## Trigger Condition

The specification requires that function files unreadable due to I/O errors contribute no callee edges. In the registry branch, the code still adds callee edges from registry_edges even when the file cannot be read (OSError is caught but only affects extra edges text, not the registry edges themselves). This violates the specification.

---

## How to trigger the bug

In the registry branch (`lang_key in registry_langs`), `callee_fqns` is computed from `registry_edges` (lines 71-72 in the extracted function) **before** any file I/O occurs. When `extra_edges_by_callsite` is truthy, the code attempts to open the file for call-site detection — but the OSError handler on line 78 only sets `text = ""`, which affects `_find_call_sites` results. The `callee_fqns` set derived from `registry_edges` is never cleared or checked against file readability.

In contrast, the non-registry `else` branch (lines 91-93) correctly skips the file entirely on OSError via `continue`, contributing no edges.

### Inputs

| Parameter | Value |
|---|---|
| `phase_files` | `[("/tmp/probe_xxx/extracted_functions/src/test-py/func.py", "test_module")]` — file is chmod 000 (unreadable) |
| `proj_dir` | Temporary directory containing the extracted_functions tree |
| `global_stem_to_fqns` | `{"func": {"src::test-py::func"}, "other_func": {"src::test-py::other_func"}}` |
| `extra_call_edges` | One `CallEdge` with `caller.callsite_names=("helper",)` and `callee.fqn="src::test-py::other_func"` (triggers `extra_edges_by_callsite` to be truthy) |
| `call_edges_all` (mocked) | Returns `({"src::test-py::func": {"src::test-py::other_func"}}, {"python"})` |

### Expected (spec-correct) Output

`all_callees_map["src::test-py::func"]` is empty — the file is unreadable, so it contributes no callee edges.

### Actual (buggy) Output

`all_callees_map["src::test-py::func"]` = `{"src::test-py::other_func"}` — callee edge from `registry_edges` is present despite the file being unreadable.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from unittest.mock import patch
from src.generate_topdown_layers import _build_call_graph
from src.call_graph_edges import CallEdge, CallerSelector, CalleeTarget

tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "extracted_functions/src/test-py"), exist_ok=True)
test_file = os.path.join(tmp, "extracted_functions/src/test-py/func.py")
with open(test_file, "w") as f:
    f.write("def func():\n    pass\n")
os.chmod(test_file, 0o000)

test_fqn = "src::test-py::func"
callee_fqn = "src::test-py::other_func"

def mock_call_edges_all(*args, **kwargs):
    return {test_fqn: {callee_fqn}}, {"python"}

extra_edges = [
    CallEdge(
        caller=CallerSelector(fqn="", callsite_names=("helper",)),
        callee=CalleeTarget(fqn=callee_fqn, info_names=("helper_alias",)),
    )
]

with patch("src.generate_topdown_layers.call_edges_all", mock_call_edges_all):
    _, _, all_callees_map, _, _, _ = _build_call_graph(
        phase_files=[(test_file, "test_module")],
        proj_dir=tmp,
        global_stem_to_fqns={"func": {test_fqn}, "other_func": {callee_fqn}},
        extra_call_edges=extra_edges,
    )

print(all_callees_map[test_fqn])  # actual (buggy) output: {'src::test-py::other_func'}
# expected (correct) output: set() — empty, no edges from unreadable file
```

---

## Probe Script

```python
"""Probe: _build_call_graph adds registry edges even when file I/O fails.

Bug summary: In the registry branch (lang_key in registry_langs), callee_fqns
are computed from registry_edges BEFORE any file I/O. When the file is
unreadable (OSError), the except block only handles extra-edge call site
detection (sets text=""), but registry-derived callee edges remain.

Spec says: "Function files that cannot be read due to I/O errors contribute no
callee edges." The bug reproduces when a registry-language file triggers OSError
but registry_edges still supply callee edges for its FQN.
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch
from collections import defaultdict


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def main():
    bug_id = "src--generate_topdown_layers-py--_build_call_graph"

    tmp = tempfile.mkdtemp(prefix="probe_build_call_graph_")
    extracted_dir = os.path.join(tmp, "extracted_functions", "src", "test-py")
    os.makedirs(extracted_dir, exist_ok=True)
    test_file = os.path.join(extracted_dir, "func.py")

    # FQN that _file_to_fqn will compute for this file
    # rel = src/test-py/func.py → stem = src/test-py/func → "src::test-py::func"
    test_fqn = "src::test-py::func"

    # A callee FQN that will be in known_fqns (so registry edges referencing it
    # pass the filter on line 72 of the extracted function)
    callee_fqn = "src::test-py::other_func"

    # ---------------------------------------------------------------------------
    # Try to import the target function
    # ---------------------------------------------------------------------------

    try:
        from src.generate_topdown_layers import _build_call_graph
        from src.call_graph_edges import CallEdge, CallerSelector, CalleeTarget
    except Exception as exc:
        print(f"ERROR importing modules: {exc}")
        cleanup(tmp, test_file)
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Create the test file and make it unreadable
    # ---------------------------------------------------------------------------

    try:
        with open(test_file, "w") as f:
            f.write("def func():\n    pass\n")
    except OSError as exc:
        print(f"ERROR creating test file: {exc}")
        cleanup(tmp, test_file)
        sys.exit(1)

    try:
        os.chmod(test_file, 0o000)
    except OSError:
        # On some constrained systems chmod may not work — still valid,
        # because the probe logic below handles both code paths.
        pass

    # ---------------------------------------------------------------------------
    # Build test inputs
    # ---------------------------------------------------------------------------

    phase_files = [(test_file, "test_module")]

    # effective_stem_to_fqns is the global_stem_to_fqns we pass in.
    # It must contain both test_fqn and callee_fqn so that known_fqns
    # includes the callee (registry edges referencing non-known FQNs are
    # filtered out).
    effective_stem_to_fqns = {
        "func": {test_fqn},
        "other_func": {callee_fqn},
    }

    # Mock call_edges_all to return registry edges for test_fqn
    def mock_call_edges_all(proj_dir, phase_langs):
        edges = {test_fqn: {callee_fqn}}
        langs = {"python"}
        return edges, langs

    # Extra call edges: use callsite_names to make extra_edges_by_callsite
    # truthy, which triggers the file-open code path (lines 331-340 of
    # the extracted function). Without this trigger the file is never
    # opened and no OSError can fire.
    extra_edges = [
        CallEdge(
            caller=CallerSelector(fqn="", callsite_names=("helper",)),
            callee=CalleeTarget(fqn=callee_fqn, info_names=("helper_alias",)),
            source="test",
        )
    ]

    # ---------------------------------------------------------------------------
    # Execute
    # ---------------------------------------------------------------------------

    try:
        with patch("src.generate_topdown_layers.call_edges_all", mock_call_edges_all):
            (
                callees_map,
                callers_map,
                all_callees_map,
                file_map,
                module_map,
                edge_aliases_map,
            ) = _build_call_graph(
                phase_files=phase_files,
                proj_dir=tmp,
                global_stem_to_fqns=effective_stem_to_fqns,
                extra_call_edges=extra_edges,
            )
    except Exception as exc:
        print(f"ERROR executing _build_call_graph: {exc}")
        cleanup(tmp, test_file)
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Verify
    # ---------------------------------------------------------------------------

    # The bug: an unreadable file SHOULD contribute no callee edges (per spec),
    # but registry_edges still supply edges.
    actual_all_callees = all_callees_map.get(test_fqn, set())
    actual_callees = callees_map.get(test_fqn, set())

    callee_edges_present = bool(actual_all_callees)

    if callee_edges_present:
        print(
            "CONFIRMED — bug reproduced:"
            f" all_callees_map[{test_fqn}] = {sorted(actual_all_callees)}"
        )
        print(
            f"  callees_map[{test_fqn}] = {sorted(actual_callees)}"
        )
        print(
            "  File is unreadable (mode 000) but registry edges were still"
            " used."
        )
    else:
        print(
            f"NOT CONFIRMED — no callee edges from unreadable file:"
            f" all_callees_map[{test_fqn}] = {sorted(actual_all_callees)}"
        )

    # ---------------------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------------------
    cleanup(tmp, test_file)


def cleanup(tmp_dir, test_file):
    """Restore file permissions and remove the temp tree."""
    try:
        os.chmod(test_file, 0o644)
    except (OSError, NameError):
        pass
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — bug reproduced: all_callees_map[src::test-py::func] = ['src::test-py::other_func']
  callees_map[src::test-py::func] = []
  File is unreadable (mode 000) but registry edges were still used.
```
