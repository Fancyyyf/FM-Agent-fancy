# Bug Report: run_entry_pipeline

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If entry_func is None, raises ValueError before any filesystem side effects occur
- proj_dir is never mutated; all filesystem mutations are confined to temporary copies that are discarded before return, regardless of success or failure
- A temporary run directory at <proj_dir>.fm-entry-run is created during execution and deleted before return
- On successful completion, <proj_dir>/fm_agent/ contains specification, reasoning, and bug-validation results scoped to functions reachable from entry_func via the static call graph; when end_funcs is non-empty, the scope is restricted to functions on at least one call-chain path from entry_func to an element of end_funcs
- On failure, any partial results already written to <proj_dir>/fm_agent/ by the inner pipeline stages are preserved in place
- The test-file exemption registered for the source file containing entry_func is guaranteed removed before return, even when the inner pipeline raises
- config.BUG_VALIDATION_MAX_RETRIES is set to 0 for the duration of this call
- When extra_call_edges_path is provided, its supplemental edges contribute to entry reachability analysis and top-down layer generation

---

### Actual Behavior

The function may terminate normally (implicitly returning None) or by raising an exception. The post-condition depends on the value of entry_func at call time.

Case A  entry_func is None:
  * The function raises ValueError("entry_func is required to run the entry pipeline").
  * The filesystem is unmodified; no temporary directory is created and proj_dir remains unchanged.
  * Global configuration and test-file exemption sets are untouched.
  * Formally: exception = ValueError ∧ (global state unchanged)

Case B  entry_func is not None:
  * The original proj_dir is resolved to its absolute path P = os.path.abspath(proj_dir). From that point onward, regardless of whether the function returns normally or propagates an exception from `_run_entry_pipeline_inner`, the following invariants hold:
    1. The directory P exists and contains a subdirectory P/fm_agent. This subdirectory holds the outputs of the pipeline run, copied back from the temporary workspace. If the pipeline completed successfully the outputs are complete; if an exception occurred the outputs may be partial.
    2. The temporary run directory that was created beside the project, named <P>.fm-entry-run, has been removed.
    3. The global setting config.BUG_VALIDATION_MAX_RETRIES equals 0.
    4. The global set of test-file exemptions is empty (clear_test_file_exemptions() was executed in the finally block, removing all previously registered exemptions).
  * If the function returns normally, it returns None; otherwise the exception raised by the inner pipeline is re-raised.

---

## Code Evidence

Line 46: work_dir = os.path.join(proj_dir, "fm_agent") and Line 55: _run_entry_pipeline_inner(...) (which ultimately populates proj_dir/fm_agent/)

---

## Trigger Condition

The specification requires that proj_dir is never mutated; however, the code creates or modifies the subdirectory proj_dir/fm_agent, which is a filesystem mutation inside proj_dir.

---

## How to trigger the bug

Call `run_entry_pipeline` with a valid `entry_func` FQN pointing to a function in the project. After the function returns (successfully or via exception), the directory `<proj_dir>/fm_agent/` will exist, contrary to the spec claim that proj_dir is never mutated.

The mutation occurs in `_run_entry_pipeline_inner`'s `finally` block (lines 485-489 in `src/entry_reasoning_pipeline.py`), which copies the generated `fm_agent/` workspace from the temporary run directory back into `proj_dir`:

```python
if os.path.isdir(run_work_dir):
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir)
    shutil.copytree(run_work_dir, work_dir, symlinks=True)
```

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Path to project directory (containing at least one extractable Python source file) |
| entry_func | FQN of an extractable function (e.g., `src::mymod-py::hello`) |

### Expected (spec-correct) Output

`proj_dir` is unmodified after the function returns — no `fm_agent/` subdirectory exists inside `proj_dir`.

### Actual (buggy) Output

`proj_dir/fm_agent/` exists after the function returns, containing the pipeline's output (specs, reasoning results, bug validation results).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile
sys.path.insert(0, ".")
from src.entry_reasoning_pipeline import run_entry_pipeline

proj_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
with open(os.path.join(proj_dir, "src", "mymod.py"), "w") as f:
    f.write("def hello():\n    return 42\n")

run_entry_pipeline(proj_dir=proj_dir, entry_func="src::mymod-py::hello")

# actual (buggy) output: fm_agent/ exists inside proj_dir → True
# expected (correct) output: fm_agent/ should NOT exist → False
print(os.path.isdir(os.path.join(proj_dir, "fm_agent")))
```

---

## Probe Script

```python
"""Probe script: run_entry_pipeline mutates proj_dir by creating proj_dir/fm_agent/.

Spec claim: "proj_dir is never mutated; all filesystem mutations are confined to
temporary copies that are discarded before return, regardless of success or failure"

This probe verifies whether proj_dir/fm_agent/ exists after run_entry_pipeline returns.
"""
import os
import sys
import shutil
import tempfile

# Ensure the package can be imported from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import run_entry_pipeline

    # Create a minimal project under a temp directory
    proj_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
    with open(os.path.join(proj_dir, "src", "mymod.py"), "w") as f:
        f.write("def hello():\n    return 42\n")

    # Call run_entry_pipeline — the function under test
    run_entry_pipeline(proj_dir=proj_dir, entry_func="src::mymod-py::hello")

    # Check mutation: did proj_dir/fm_agent/ get created?
    actual = os.path.isdir(os.path.join(proj_dir, "fm_agent"))
    # Spec says proj_dir is never mutated → fm_agent should NOT exist
    expected = False
    passed = actual != expected  # True → bug reproduced (actual mutation, spec says none)

    shutil.rmtree(proj_dir, ignore_errors=True)

except Exception as e:
    # Even on exception, check if proj_dir/fm_agent/ exists
    # (the finally block in _run_entry_pipeline_inner copies back partial results)
    fm_agent_exists = os.path.isdir(os.path.join(proj_dir, "fm_agent"))
    actual = fm_agent_exists
    expected = False
    passed = actual != expected
    print(f"ERROR: {e}")

if passed:
    print(f"CONFIRMED — actual: proj_dir/fm_agent exists={actual!r} | expected: exists={expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: proj_dir/fm_agent exists={actual!r}")
```

### Probe Output

```
Generated 1 batch prompt(s) for phase 1 layers 0 in /tmp/tmpirx90iqy.fm-entry-run/fm_agent/spec_prompts/batch_prompts_fm-entry-run_phase01
[Pipeline] Building codegraph index...
[Pipeline] codegraph index built.
Extraction complete: 1 written, 0 skipped.
[EntryPipeline] Selected 1 of 1 function(s) from entry src::mymod-py::hello.
[Pipeline] Building codegraph index...
[Pipeline] codegraph index built.
[EntryPipeline] Trimmed /tmp/tmpirx90iqy.fm-entry-run: kept 1 function(s), removed 0 function(s), deleted 0 source file(s).
[Pipeline] Stage 1/6: Generating phase plan...
[Pipeline] Stage 2/6: Generating domain context...
[Pipeline] Rebuilding codegraph index for current working tree...
[Pipeline] codegraph index built.
[Pipeline] Stage 3/6: Extracting functions from source files...
  WRITE: fm_agent/extracted_functions/src/mymod-py/hello.py
Extraction complete: 1 written, 0 skipped.
Validation passed: every extracted file contains exactly one function.
[Pipeline] Stage 4/6: Collecting file list...
[Pipeline] Stage 5/6: Generating topdown layers...
[TopdownLayers] Phase 1 (Core Module): 1 functions, 1 layers -> spec_prompts/phase_01_topdown_layers.json
[Pipeline] Stage 6/6: Generating specs & verification...
[Pipeline] Stage 6/6: Phase 1/1 — Core Module, Layer 0/0
Functions pending verification: 1
[1/1] fm_agent/extracted_functions/src/mymod-py/hello.py: ✔
[Pipeline] Done.
[EntryPipeline] Copied generated fm_agent/ to /tmp/tmpirx90iqy/fm_agent.
[EntryPipeline] Bugs (mismatches): 0
[EntryPipeline] Done. Results in /tmp/tmpirx90iqy/fm_agent.
CONFIRMED — actual: proj_dir/fm_agent exists=True | expected: exists=False
```
