# Bug Report: _select_functions_by_source

**Source file:** `/home/fancy/Projects_Vault/FM-Agent_qwen_7d490/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns two mappings keyed by project-relative source-file path, each value being the set of distinct function identifiers (names as they appear in the source) contributed by that file: (1) the first maps every source file that contributed at least one extracted function to the identifiers of ALL extractable functions of that file across the whole project; (2) the second maps source files to the identifiers of exactly those functions reachable from entry_func in the project call graph  including entry_func itself, with reachability evaluated over the call graph augmented by any supplemental edges  further narrowed to functions lying on a call chain from entry_func to at least one member of end_funcs whenever end_funcs is non-empty. Every reachable function is included regardless of call-chain depth, and a file appears in a mapping only if it contributes at least one function to that mapping. proj_dir is read but never modified: extraction, index building, and all scratch state used for selection are confined to a temporary copy of the project created beside proj_dir, which is removed in full before return whether selection succeeds or raises. Raises ValueError when no extractable source files exist under proj_dir, when no extractable functions are found, when entry_func is not among the extracted functions, or when end_funcs is non-empty and none of its members is reachable from entry_func; when at least one member of end_funcs is reachable, individually unreachable members are tolerated and do not cause failure.

---

### Actual Behavior

Upon successful return the function yields a 2-tuple (all_by_source, keep_by_source). all_by_source is a dict mapping each project-relative source-file path to the collection of every extractable function defined in that file across the entire project. keep_by_source is a dict mapping each project-relative source-file path to the collection of selected functions, i.e. those reachable from entry_func in the call graph; when end_funcs is a non-empty sequence the selection is further restricted to functions lying on at least one call chain from entry_func to some member of end_funcs (via _restrict_to_chains), and when end_funcs is None or empty the selection comprises all functions reachable from entry_func. extra_call_edges, when not None, are merged into the call graph before reachability analysis. The temporary selection directory at proj_dir + '.fm-entry-select' (and all its contents including the codegraph index, the fm_agent workspace, and phases.json) has been removed before the function returns. proj_dir is never modified. Formally: let CG = _build_call_graph(phase_files, work_dir, extra_call_edges); let reachable = BFS/DFS closure from entry_func over CG; let selected = reachable if (end_funcs is None or len(end_funcs)==0) else _restrict_to_chains(CG, entry_func, end_funcs); then keep_by_source = group_by_source(selected) and all_by_source = group_by_source(all_extracted).  path p: p  proj_dir-tree  p unchanged. The sibling directory proj_dir + '.fm-entry-select' does not exist after return. Exception paths: (1) If _enumerate_source_files returns an empty list, a ValueError is raised with a message referencing proj_dir; the selection directory is still cleaned up. (2) If _build_call_graph or run_extraction raises, the exception propagates after cleanup of the selection directory. (3) If entry_func is not present as a key in the built call graph, the behaviour follows _restrict_to_chains or reachability semantics (empty keep_by_source or KeyError depending on implementation). In all cases, proj_dir remains unmodified and the selection copy is discarded.

---

## Code Evidence

Line 38: run_extraction(sel_dir, work_dir=work_dir, force=True)
Line 39: phase_files = _collect_phase_files(work_dir, phase)
Line 40: if not phase_files:

---

## Trigger Condition

Condition B explicitly requires: 'Raises ValueError when  entry_func is not among the extracted functions.' Condition A, however, states: 'If entry_func is not present as a key in the built call graph, the behaviour follows _restrict_to_chains or reachability semantics (empty keep_by_source or KeyError depending on implementation).' No ValueError is raised. A concrete input: a project with one file defining only 'foo', called with entry_func='nonexistent_func'. The code proceeds to build the call graph, finds no key for 'nonexistent_func', and either returns an empty keep_by_source or propagates a KeyErrorneither of which is the ValueError mandated by the specification. The visible code (lines 38-40) performs extraction and collects phase files but never validates that entry_func appears among the extracted functions before continuing to call-graph construction and reachability analysis.

---

## How to trigger the bug

The reported trigger is a project with one file defining only `foo`, calling
the entry-point-scoped pipeline with `entry_func='nonexistent_func'`. The
report claims the code never validates that `entry_func` appears among the
extracted functions, so the call would return an empty `keep_by_source` or
propagate a `KeyError` instead of the spec-mandated `ValueError`.

Three probe attempts exercised exactly this path through the public entry
point (`main.run_entry_pipeline`, with the FM-Agent workflow driver
`main.run_pipeline` stubbed per the self-validation guard). In every attempt
the code raised the spec-mandated `ValueError` before any call-graph
reachability work, because the current source validates the entry point
(`src/entry_reasoning_pipeline.py`, in `_select_functions_by_source`):

```py
all_fqns = {_file_to_fqn(fp, work_dir) for fp, _mod in phase_files}

if entry_func not in all_fqns:
    raise ValueError(
        f"entry_func {entry_func!r} not found among extracted functions under proj_dir"
    )
```

The bug therefore could not be reproduced: the implemented behavior already
satisfies the specification clause under test.

### Inputs

| Parameter | Value (attempt 1) | Value (attempt 2) | Value (attempt 3, final) |
|-----------|-------------------|-------------------|--------------------------|
| `proj_dir` | fresh temp dir with `foo.py` defining only `foo` | fresh temp dir with `foo.py` (`foo` calls `bar`) and `baz.py` (defines `bar`) | same as attempt 2 |
| `entry_func` | `'nonexistent_func'` | `'foo-py::nonexistent_func'` (FQN-shaped) | `'bar'` (bare name of an extracted function whose FQN is `'baz-py::bar'`) |
| `end_funcs` | `None` | `None` | `['foo-py::foo']` (proves the entry check fires before chain restriction) |
| `extra_call_edges` | `None` | `None` | `None` |

### Expected (spec-correct) Output

`ValueError` whose message reports that `entry_func` is not found among the
extracted functions under `proj_dir`.

### Actual (buggy) Output

No buggy output was observable. All attempts raised the spec-correct
`ValueError`; the final attempt produced:
`ValueError: entry_func 'bar' not found among extracted functions under proj_dir`
— identical in kind and intent to the expected output, so the reported bug did
not reproduce.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point; the workflow
   driver is stubbed so no FM-Agent workflow starts):

```py
import os, sys, tempfile
import main

main.run_pipeline = lambda *a, **k: None  # guard: never start an FM-Agent workflow

proj_dir = os.path.join(tempfile.mkdtemp(), "proj")
os.makedirs(proj_dir)
with open(os.path.join(proj_dir, "foo.py"), "w") as f:
    f.write("def foo():\n    return 1\n")

try:
    main.run_entry_pipeline(proj_dir, entry_func="nonexistent_func", end_funcs=None)
    print("returned normally (bug reproduced)")
except ValueError as e:
    print(f"ValueError raised (spec-correct): {e}")
# actual output: ValueError raised (spec-correct): entry_func 'nonexistent_func' not found among extracted functions under proj_dir
# expected (buggy) output claimed by the report: returns normally with empty keep_by_source, or raises KeyError
```

---

## Probe Script

```py
"""Probe for bug `src--entry_reasoning_pipeline-py--_select_functions_by_source`.

Attempt 3 — different inputs: entry_func='bar' is the BARE name of a real
function in the fixture (baz.py defines bar), while extracted identities are
FQNs ('baz-py::bar'), so 'bar' is not among the extracted functions; the
strict-membership check must still raise ValueError. end_funcs is non-empty to
prove the entry_func validation fires before any chain restriction.

Spec claim under test: the pipeline MUST raise ValueError when entry_func is
not among the extracted functions. Reported actual behavior: no validation —
the function proceeds and either returns an empty keep_by_source or raises
KeyError.

FM-Agent self-validation guard: main.run_pipeline is stubbed with a recording
no-op so no FM-Agent workflow (LLM/OpenCode) can start. All fixtures live in a
fresh temporary directory owned by this probe.
"""
import os
import shutil
import sys
import tempfile

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

probe_tmp = None
try:
    import main

    workflow_calls = []

    def _workflow_stub(*args, **kwargs):
        workflow_calls.append((args, kwargs))
        return None

    main.run_pipeline = _workflow_stub

    # Fresh fixture project: foo.py calls bar(), defined in baz.py.
    probe_tmp = tempfile.mkdtemp(prefix="fm_probe_entry_select_")
    proj_dir = os.path.join(probe_tmp, "proj")
    os.makedirs(proj_dir)
    with open(os.path.join(proj_dir, "foo.py"), "w") as f:
        f.write("def foo():\n    return bar()\n")
    with open(os.path.join(proj_dir, "baz.py"), "w") as f:
        f.write("def bar():\n    return 42\n")
except Exception as e:
    print(f"ERROR: probe setup failed: {type(e).__name__}: {e}")
    sys.exit(1)

expected = "ValueError stating entry_func is not among the extracted functions"
passed = False
outcome = None
try:
    result = main.run_entry_pipeline(
        proj_dir, entry_func="bar", end_funcs=["foo-py::foo"]
    )
    outcome = (
        f"returned normally: {result!r} "
        f"(workflow stub invocations: {len(workflow_calls)})"
    )
    passed = True  # spec mandates ValueError; a plain return reproduces the bug
except ValueError as e:
    msg = str(e)
    if "entry_func" in msg:
        outcome = f"raised ValueError: {msg}"
        passed = False  # spec-correct behavior
    else:
        print(f"ERROR: unrelated ValueError before reaching the check: {msg}")
        shutil.rmtree(probe_tmp, ignore_errors=True)
        sys.exit(1)
except Exception as e:
    outcome = f"raised {type(e).__name__} instead of ValueError: {e}"
    passed = True  # spec mandates ValueError; any other outcome reproduces the bug
finally:
    shutil.rmtree(probe_tmp, ignore_errors=True)

if passed:
    print(f"CONFIRMED — actual: {outcome} | expected: {expected}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {outcome}")

```

### Probe Output

```
[Pipeline] Building codegraph index...
[Pipeline] codegraph index built.
Extraction complete: 2 written, 0 skipped.
NOT CONFIRMED — actual matched expected: raised ValueError: entry_func 'bar' not found among extracted functions under proj_dir
```
