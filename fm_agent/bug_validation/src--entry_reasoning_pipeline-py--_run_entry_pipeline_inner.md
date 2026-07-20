# Bug Report: _run_entry_pipeline_inner

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- proj_dir is never mutated by this function or any callee transitively invoked
- A temporary directory at <proj_dir>.fm-entry-run is created during execution and destroyed before return, regardless of success or failure
- The set of functions operated on is the subset reachable from entry_func via the static call graph; when end_funcs is non-empty, the set is further restricted to functions on at least one call-chain path from entry_func to some member of end_funcs
- On successful completion, work_dir contains the complete fm_agent/ output produced by running the standard pipeline on the trimmed project copy
- On failure, any partial fm_agent/ results already produced within the temporary run directory are copied to work_dir before the temporary directory is destroyed
- The number of MISMATCH verdicts found in work_dir/logic_verification_results/ is printed to stdout on every run
- When extra_call_edges_path is provided, its supplemental call edges contribute to the reachability analysis used to determine the function subset

---

### Actual Behavior

After the function terminates (whether normally or by exception):
(1) The temporary directory `run_dir = proj_dir + '.fm-entry-run'` is deleted.
(2) If the subdirectory `run_work_dir = run_dir + '/fm_agent'` existed at the moment the finally block executed, then `work_dir` (which is `proj_dir + '/fm_agent'`) is replaced by a copy of `run_work_dir`. If `run_work_dir` did not exist, `work_dir` is left unchanged (except for the conditional deletion that only fires when `run_work_dir` exists, so its prior state is preserved).
(3) On normal return:
   - The standard output contains a line showing the number of mismatch verdicts from `<work_dir>/logic_verification_results/`.
   - The function returns `None`.
(4) On an exception that propagates out of the function:
   - The mismatch count and the final two `print` statements are not executed.
   - The exception object is raised to the caller.

Formally:
Let `proj_dir` be the pre-condition absolute path.
Define `run_dir  proj_dir + ".fm-entry-run"`, `run_work_dir  run_dir + "/fm_agent"`, `work_dir  proj_dir + "/fm_agent"`.
Post-call state satisfies:
   run_dir
   (  run_work_dir at finally block  work_dir = copy_of(run_work_dir) )
   ( NormalReturn 
        ( run_work_dir at finally  work_dir = copy_of(run_work_dir))
         stdout = stdout before prints ++ mismatch_report_lines
         return_value = None
    )
   ( ExceptionRaised 
        stdout = stdout before prints
    )

---

## Code Evidence

Line 67: mismatches = _count_mismatches(os.path.join(work_dir, "logic_verification_results"))
Line 68: print(f"[EntryPipeline] Bugs (mismatches): {mismatches}")

---

## Trigger Condition

The specification requires that "The number of MISMATCH verdicts found in work_dir/logic_verification_results/ is printed to stdout on every run", i.e., regardless of success or failure. The code only prints the mismatch count after the try-finally block (lines 67-68), which is only reached on normal return. When an exception propagates out of the function, the finally block executes but lines 67-68 are skipped, so the count is not printed, violating the specification.

---

## How to trigger the bug

When `_run_entry_pipeline_inner` encounters an exception inside its `try` block (e.g., from `_trim_project_in_place` or `run_pipeline`), the `finally` block executes (cleaning up the run directory and copying partial results), but the mismatch-count `print` statement on lines 494-495 is skipped because it sits *after* the `try-finally` block. The exception propagates to the caller without the count ever being printed, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `<temp directory>` |
| entry_func | `"src::dummy-py::dummy"` |
| end_funcs | `[]` |
| Injected failure | `RuntimeError("BOOM")` raised inside `_trim_project_in_place` (within the try block) |

### Expected (spec-correct) Output

`[EntryPipeline] Bugs (mismatches): 0` should appear in stdout even when an exception propagates.

### Actual (buggy) Output

No mismatch count line is printed. Only the exception propagates to the caller.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.entry_reasoning_pipeline import run_entry_pipeline

# Patch _trim_project_in_place to raise inside the try block
with patch("src.entry_reasoning_pipeline._select_functions_by_source",
           return_value=({}, {})):
    with patch("src.entry_reasoning_pipeline._make_run_copy"):
        with patch("src.entry_reasoning_pipeline.try_codegraph_init"):
            with patch("src.entry_reasoning_pipeline._trim_project_in_place",
                       side_effect=RuntimeError("BOOM")):
                run_entry_pipeline(
                    "/tmp/fm-probe",
                    entry_func="src::dummy-py::dummy",
                    end_funcs=[],
                )
# actual (buggy) output: <no mismatch count printed; exception propagates>
# expected (correct) output: [EntryPipeline] Bugs (mismatches): 0
```

---

## Probe Script

```python
"""Probe for bug: mismatch count not printed on exception in _run_entry_pipeline_inner.

Spec says: "The number of MISMATCH verdicts found in work_dir/logic_verification_results/
is printed to stdout on every run"
Bug: lines after try-finally are skipped when exception propagates, so count is not printed.
"""

import sys
import os
import io
import tempfile
import shutil
from unittest.mock import patch

proj_dir = tempfile.mkdtemp(prefix="fm-probe-")
real_stdout = sys.__stdout__

try:
    import config
    from src.entry_reasoning_pipeline import run_entry_pipeline

    # Capture stdout during the function call
    captured = io.StringIO()
    sys.stdout = captured

    error_raised = False
    exception_caught = None

    try:
        with patch(
            "src.entry_reasoning_pipeline._select_functions_by_source",
            return_value=({}, {}),
        ):
            with patch("src.entry_reasoning_pipeline._make_run_copy"):
                with patch("src.entry_reasoning_pipeline.try_codegraph_init"):
                    with patch(
                        "src.entry_reasoning_pipeline._trim_project_in_place",
                        side_effect=RuntimeError(
                            "BOOM: injected failure inside try block"
                        ),
                    ):
                        run_entry_pipeline(
                            proj_dir,
                            entry_func="src::dummy-py::dummy",
                            end_funcs=[],
                        )
    except RuntimeError as e:
        error_raised = True
        exception_caught = e
    except Exception as e:
        error_raised = True
        exception_caught = e

    function_output = captured.getvalue()

    # Restore real stdout for printing verdict
    sys.stdout = real_stdout

    has_mismatch_line = "[EntryPipeline] Bugs (mismatches):" in function_output

    if error_raised and not has_mismatch_line:
        print(
            "CONFIRMED — exception propagated "
            f"({exception_caught}) "
            "but mismatch count was NOT printed to stdout"
        )
    elif error_raised and has_mismatch_line:
        print(
            "NOT CONFIRMED — exception propagated "
            "but mismatch count WAS printed "
            "(spec may already be satisfied)"
        )
    elif not error_raised:
        print(
            "NOT CONFIRMED — expected RuntimeError was not raised; "
            "function completed without exception"
        )
    else:
        print("NOT CONFIRMED — unexpected program state")

except Exception as e:
    sys.stdout = sys.__stdout__
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

finally:
    shutil.rmtree(proj_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — exception propagated (BOOM: injected failure inside try block) but mismatch count was NOT printed to stdout
```
