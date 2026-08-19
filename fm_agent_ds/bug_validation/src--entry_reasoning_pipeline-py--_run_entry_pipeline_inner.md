# Bug Report: _run_entry_pipeline_inner

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Has executed the full FM-Agent reasoning pipeline on a temporary, isolated copy of the project containing only the source files for functions on directed call-graph paths from entry_func to end_funcs. When end_funcs is None or empty: all functions reachable from entry_func in the call graph are included instead. After execution: the generated fm_agent/ workspace is present at work_dir and, for every processed function, contains behavioral specifications (.spec.json and .info.json files) under extracted_functions/, reasoning verdicts under logic_verification_results/, and bug-validation reports under bug_validation/. The source files under proj_dir are never modified. If the pipeline terminates without completing all functions, partial results for completed functions are preserved at work_dir. No temporary files or directories remain at the path formed by joining proj_dir with the literal string '.fm-entry-run'.

---

### Actual Behavior

Upon exit from _run_entry_pipeline_inner, the following holds:
Let run_dir = proj_dir + '.fm-entry-run', run_work_dir = os.path.join(run_dir, 'fm_agent'), work_dir = os.path.join(proj_dir, 'fm_agent').
- proj_dir exists and its content except work_dir is unchanged.
- Either (a) the function terminated normally: run_dir does not exist, work_dir exists and contains the complete pipeline results originally generated in run_work_dir, and the standard output contains a line of the form '[EntryPipeline] Bugs (mismatches): <count>'; or (b) the function terminated with an exception: then one of the following subcases:
   (b1) The exception originated before or during the try block and the finally block completed without error: run_dir does not exist; if run_work_dir was created by the pipeline before the exception, its contents were copied to work_dir, replacing any previous work_dir content; otherwise work_dir is unchanged from its pre-call state. The exception is re-raised.
   (b2) The exception originated during the finally block's copy operation (shutil.copytree): then run_dir still exists (possibly with partial content), work_dir has been removed if it existed prior to the call, and the exception propagates.

---

## Code Evidence

Line 65: shutil.rmtree(work_dir)

---

## Trigger Condition

Specification B requires that no temporary files or directories remain at the path formed by joining proj_dir with '.fm-entry-run'. When shutil.rmtree(work_dir) raises an exception inside the finally block, the subsequent cleanup of run_dir on line 68 is skipped, and run_dir persists. Even if the exception is from a file permission problem that could be considered an environmental error, the concrete input described produces a violation of the absolute 'no leftovers' requirement.

---

## How to trigger the bug

The `finally` block in `_run_entry_pipeline_inner` (lines 520-528 of `src/entry_reasoning_pipeline.py`) first attempts to remove `work_dir` (the pre-existing `fm_agent/` directory) via `shutil.rmtree(work_dir)` on line 525. If that call raises an exception — e.g., a `PermissionError` because another process holds a file handle inside `fm_agent/`, or file permissions prevent deletion — the exception propagates immediately. When this happens, the `shutil.rmtree(run_dir, ignore_errors=True)` call on line 528 is never reached, and `run_dir` (the `proj_dir + '.fm-entry-run'` directory) is left behind, violating the specification's "no temporary files or directories remain" requirement.

The root cause is that `shutil.rmtree(work_dir)` on line 525 is not wrapped in a `try/except` block, so any exception it raises escapes the `finally` block, preventing the guaranteed cleanup of `run_dir` on line 528.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | any valid project directory |
| `entry_func` | any valid entry function FQN |
| `end_funcs` | `None` |
| Condition | `work_dir` (`proj_dir/fm_agent`) is not removable (e.g., permissions 000) |

### Expected (spec-correct) Output

`run_dir` (`proj_dir + '.fm-entry-run'`) does not exist after the function returns (whether normally or with an exception). All temporary files and directories are cleaned up.

### Actual (buggy) Output

When `shutil.rmtree(work_dir)` raises an exception (e.g., `PermissionError`), `run_dir` persists on disk because `shutil.rmtree(run_dir, ignore_errors=True)` on line 528 is never reached.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import shutil
import tempfile

tmp = tempfile.mkdtemp()
proj_dir = os.path.join(tmp, "proj")
os.makedirs(proj_dir)
run_dir = proj_dir + ".fm-entry-run"
run_work_dir = os.path.join(run_dir, "fm_agent")
work_dir = os.path.join(proj_dir, "fm_agent")
os.makedirs(run_work_dir)
os.makedirs(work_dir)

# Make work_dir unremovable
os.chmod(work_dir, 0o000)

# Replicate the finally-block pattern from _run_entry_pipeline_inner
try:
    try:
        pass  # simulated pipeline execution
    finally:
        if os.path.isdir(run_work_dir):
            if os.path.isdir(work_dir):
                shutil.rmtree(work_dir)  # raises PermissionError
            shutil.copytree(run_work_dir, work_dir, symlinks=True)
        shutil.rmtree(run_dir, ignore_errors=True)  # never reached
except Exception:
    pass

# actual (buggy) output: run_dir still exists
print("run_dir exists:", os.path.exists(run_dir))  # True (bug)
# expected (correct) output: run_dir does not exist  # False

# Cleanup
os.chmod(work_dir, 0o700)
shutil.rmtree(tmp, ignore_errors=True)
```

---

## Probe Script

```python
"""Probe: _run_entry_pipeline_inner finally block leaves run_dir behind
when shutil.rmtree(work_dir) raises an exception.

Replicates the exact finally-block pattern (lines 520-528) from
src/entry_reasoning_pipeline.py, forcing shutil.rmtree(work_dir) to
fail via os.chmod(0o000) and checking whether run_dir persists.
"""

import sys
import os
import shutil
import tempfile

tmp = tempfile.mkdtemp()

# ---------------------------------------------------------------------------
# Replicate the _run_entry_pipeline_inner finally-block scenario.
# Source lines referenced (src/entry_reasoning_pipeline.py):
#
#   run_dir      = proj_dir + ".fm-entry-run"                   # line 483
#   run_work_dir = os.path.join(run_dir, "fm_agent")            # line 484
#   work_dir     = os.path.join(proj_dir, "fm_agent")           # line 298
#
#   finally:
#       if os.path.isdir(run_work_dir):                         # line 523
#           if os.path.isdir(work_dir):                         # line 524
#               shutil.rmtree(work_dir)                         # line 525
#           shutil.copytree(run_work_dir, work_dir, symlinks=…) # line 526
#       shutil.rmtree(run_dir, ignore_errors=True)              # line 528
# ---------------------------------------------------------------------------

try:
    proj_dir = os.path.join(tmp, "proj")
    os.makedirs(proj_dir)

    run_dir = proj_dir + ".fm-entry-run"
    run_work_dir = os.path.join(run_dir, "fm_agent")
    work_dir = os.path.join(proj_dir, "fm_agent")

    os.makedirs(run_work_dir)
    os.makedirs(work_dir)

    # Force shutil.rmtree(work_dir) to fail by revoking all permissions.
    os.chmod(work_dir, 0o000)

    # ---------------------------------------------------------------
    # EXACT replica of the finally-block pattern (lines 520-528).
    # The exception from rmtree(work_dir) must propagate so that the
    # subsequent rmtree(run_dir, …) on line 528 is never reached —
    # matching the real behaviour.
    # ---------------------------------------------------------------
    caught = None
    try:
        try:
            pass  # simulated successful pipeline execution
        finally:
            if os.path.isdir(run_work_dir):
                if os.path.isdir(work_dir):
                    shutil.rmtree(work_dir)                               # line 525
                shutil.copytree(run_work_dir, work_dir, symlinks=True)    # line 526
            shutil.rmtree(run_dir, ignore_errors=True)                    # line 528
    except Exception as exc:
        caught = exc

    # Restore permissions so we can inspect.
    os.chmod(work_dir, 0o700)

    run_dir_exists = os.path.exists(run_dir)

    if caught is not None and run_dir_exists:
        print(
            f"CONFIRMED — shutil.rmtree(work_dir) raised {type(caught).__name__}, "
            f"causing run_dir to persist at '{run_dir}'. "
            f"Spec requires no temp files/dirs remain at that path."
        )
    elif caught is not None and not run_dir_exists:
        print(f"NOT CONFIRMED — exception occurred but run_dir was still cleaned up")
    elif caught is None and run_dir_exists:
        print(f"NOT CONFIRMED — no exception but run_dir still persists (unexpected)")
    else:
        print(f"NOT CONFIRMED — no exception, run_dir cleaned up as expected")

except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

finally:
    # Full cleanup: restore perms on any remaining dirs and remove everything.
    for d in (os.path.join(tmp, "proj", "fm_agent"), os.path.join(tmp, "proj.fm-entry-run", "fm_agent")):
        if os.path.isdir(d):
            os.chmod(d, 0o700)
    shutil.rmtree(tmp, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — shutil.rmtree(work_dir) raised PermissionError, causing run_dir to persist at '/tmp/tmpgug6hwdr/proj.fm-entry-run'. Spec requires no temp files/dirs remain at that path.
```
