# Bug Report: streaming_reasoner

**Source file:** `src/verification-py/streaming_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Every file in input_dir (scoped to file_list when provided) whose is_file_ready()
    returns True will be submitted to _verify_single_file exactly once; a readied
    file that was in already_processed is NOT resubmitted
  - A verification result JSON is written to output_dir for every submitted file,
    mirroring the relative path structure of input_dir; the verdict field in each
    result is one of: "MATCH", "MISMATCH", "ERROR", "SKIPPED"
  - For every verified file whose verdict is "MISMATCH" and proj_dir is not None,
    a bug-validation task is submitted via _validate_single_bug; the validation
    writes a result JSON at proj_dir/bug_validation/<bug_id>.result.json where
    bug_id is derived from the result JSON path by stripping the
    fm_agent/logic_verification_results/ prefix, removing ".json", and replacing
    "/" with "--"
  - Progress output is printed for each completed verification: MATCH and SKIPPED
    files are marked with a green check, confirmed bugs with a red cross; each
    line is prefixed with "[<N>/<total>] <relative_path>: <label>"
  - When all expected files have been verified, all reasoning futures are done,
    and no validation futures remain in-flight, the loop exits normally
  - When spec_procs is provided and every process has exited via _spec_task_done,
    and not all expected files are ready: the function exits with a warning.
    If no files received specs at all, the warning states no [SPEC]/[INFO] markers
    were observed; otherwise it reports how many files are missing specs and
    lists each as "[pending]"
  - On KeyboardInterrupt: all in-flight reasoning and validation futures are
    waited on to completion before the function returns
  - If proj_dir is not None, _generate_validation_summary is called after all
    processing ends (normal exit, early-exit on stalled specs, or interrupt),
    producing proj_dir/bug_validation/summary.json
  - Return... (line truncated to 2000 chars)

---

### Actual Behavior

Let state S be the program state after the precondition, with variables as defined there. Define break_condition = (expected_files is not None  processed  expected_files  reasoning_futures =   validation_futures = )  (spec_procs is not None  ( p  spec_procs : _spec_task_done(p))  ((expected_files or set()) \ processed)    reasoning_futures =   validation_futures = ). After execution of the code block (lines 121171) starting from S, if break_condition holds then: the loop is exited, the function returns processed; reasoning_futures and validation_futures are empty; if proj_dir  None then _generate_validation_summary(work_dir) has been called (side effect); all other variables remain unchanged. If break_condition does not hold then: time.sleep(poll_interval) executed, the while True loop is about to begin its next iteration, and all variables (processed, submitted, reasoning_futures, validation_futures, completed_count, output_dir, expected_files, num_functions, work_dir, proj_dir, input_dir, EXT_TO_LANG, MAX_WORKERS, resume, executor) retain the same values as in the precondition. No KeyboardInterrupt occurred (per precondition).

---

## Code Evidence

Line 133: if _all_procs is not None and all(_spec_task_done(p) for p in _all_procs):
Line 135: if unready and not reasoning_futures and not validation_futures:

---

## Trigger Condition

Specification B.6 requires the function to exit with a warning as soon as spec_procs processes have all exited and not all expected files are ready. The code adds extra conditions `not reasoning_futures` and `not validation_futures`, delaying exit until those inflight futures finish. This violates the immediate-exit behaviour implied by B.6.

---

## How to trigger the bug

The bug manifests when all three conditions hold simultaneously:
1. `spec_procs` is provided and all processes have exited (all `_spec_task_done()` return True)
2. Not all expected files are ready (some files never receive [SPEC]/[INFO] markers)
3. There are active `reasoning_futures` or `validation_futures` still in-flight

In this scenario, per spec B.6 the function should exit immediately with a warning. Instead, the code at line 209 (`src/verification.py`) requires `not reasoning_futures and not validation_futures` to also be true, so the function keeps polling until those futures complete — delaying the exit indefinitely.

### Inputs

| Parameter | Value |
|-----------|-------|
| `input_dir` | temp directory containing `test_func.py` (ready) |
| `output_dir` | temp directory for output |
| `file_list` | `["test_func.py", "nonexistent_func.py"]` |
| `spec_procs` | `[mock process with poll() -> 0]` |
| `poll_interval` | `0.1` |
| `proj_dir` | `None` |

### Expected (spec-correct) Output

The function should exit immediately (within < 1s) with a warning indicating that spec generation processes exited but `nonexistent_func.py` is missing specs.

### Actual (buggy) Output

The function continues polling in its main loop, waiting for the in-flight `reasoning_future` (from the submitted `test_func.py` verification) to complete before checking the spec_procs early-exit condition again. This can delay exit arbitrarily (for as long as reasoning takes).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.verification import streaming_reasoner
import tempfile, os, time, threading
from unittest.mock import patch

tmpdir = tempfile.mkdtemp()
input_dir = os.path.join(tmpdir, "input")
output_dir = os.path.join(tmpdir, "output")
os.makedirs(input_dir)
os.makedirs(output_dir)

# Create ready file
with open(os.path.join(input_dir, "test_func.py"), "w") as f:
    f.write("[SPEC]\n[SPEC]\n[INFO]\n[INFO]\ndef f(): pass\n")

mock = type("P", (), {"poll": lambda: 0})()
spec_procs = [mock]

def slow(*a, **kw):
    time.sleep(30)
    return ("x", "MATCH")

with patch("src.verification._verify_single_file", side_effect=slow), \
     patch("src.verification._validate_single_bug", return_value=None), \
     patch("src.verification._generate_validation_summary", return_value=None):
    t = threading.Thread(target=streaming_reasoner, args=(
        input_dir, output_dir, ["test_func.py", "nonexistent.py"], spec_procs))
    t.start()
    t.join(timeout=5)
    print("BUG CONFIRMED" if t.is_alive() else "NOT CONFIRMED")
// actual (buggy) output: Function does not exit within 5s; keeps polling
// expected (correct) output: Function exits immediately with a warning
```

---

## Probe Script

```python
"""
Probe script for bug: src--verification-py--streaming_reasoner

Bug: streaming_reasoner adds extra guards `not reasoning_futures and not validation_futures`
to the early-exit condition (line 209 in src/verification.py), delaying exit until
in-flight reasoning/validation futures complete. Per spec B.6, the function should
exit immediately with a warning when spec_procs are all done and not all expected
files are ready.

Probe strategy:
  - Set up input_dir with one ready file and one nonexistent (always unready) file
  - Mock spec_procs as all done
  - Mock _verify_single_file to block for 30s (keeps reasoning_futures non-empty)
  - Run streaming_reasoner with a 5-second timeout in a thread
  - If the function doesn't exit within 5s -> BUG CONFIRMED (it's waiting for the
    slow reasoning future instead of exiting immediately per spec)
"""

import sys
import os
import tempfile
import threading
import time
import shutil
import logging
from unittest.mock import patch

logging.basicConfig(level=logging.WARNING)

# Ensure the project root is on sys.path so that `src.verification` can be imported
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

import src.verification as verification_module

result = {"exited": False, "exception": None, "warning_printed": False}


def run_reasoner(input_dir, output_dir, file_list, spec_procs):
    """Run streaming_reasoner in a thread, capturing whether it exits."""
    try:
        verification_module.streaming_reasoner(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=file_list,
            spec_procs=spec_procs,
            poll_interval=0.1,
            resume=False,
        )
        result["exited"] = True
    except Exception as e:
        result["exception"] = str(e)


try:
    # ---- Stage 1: Set up temp directories -----------------------------------
    tmpdir = tempfile.mkdtemp(prefix="probe_streaming_")
    input_dir = os.path.join(tmpdir, "input")
    output_dir = os.path.join(tmpdir, "output")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # ---- Stage 2: Create a "ready" file (2+ [SPEC], 2+ [INFO]) --------------
    ready_file = os.path.join(input_dir, "test_func.py")
    ready_content = "\n".join([
        "[SPEC] test_func pre",
        "[SPEC] test_func post",
        "[INFO] test_func is_file_ready",
        "[INFO] test_func helper",
        "def test_func():",
        "    return 42",
        "",
    ])
    with open(ready_file, "w") as f:
        f.write(ready_content)

    # file_list: includes ready file + a nonexistent file (always unready)
    file_list = [
        "test_func.py",              # exists, will be ready -> submitted
        "nonexistent_func.py",       # never exists -> always unready
    ]

    # ---- Stage 3: Mock spec_procs as "all done" -----------------------------
    # _spec_task_done checks poll() for Popen handles, so mock a Popen-like obj
    mock_proc = type("MockProc", (), {"poll": lambda: 0})()
    spec_procs = [mock_proc]

    # ---- Stage 4: Mock _verify_single_file to block 30s ---------------------
    # This keeps reasoning_futures non-empty during the probe window.
    def slow_verify(*_args, **_kwargs):
        time.sleep(30)
        return ("fake_path.py", "MATCH")

    # ---- Stage 5: Run with timeout ------------------------------------------
    with patch.object(verification_module, "_verify_single_file",
                      side_effect=slow_verify):
        with patch.object(verification_module, "_validate_single_bug",
                          return_value=None):
            with patch.object(verification_module, "_generate_validation_summary",
                              return_value=None):
                t = threading.Thread(
                    target=run_reasoner,
                    args=(input_dir, output_dir, file_list, spec_procs),
                    daemon=True,
                )
                t.start()
                t.join(timeout=5)

                if t.is_alive():
                    # Bug confirmed: function is still running after 5s.
                    # Per spec B.6, it should have exited immediately when
                    # spec_procs completed and files were unready.
                    print(
                        "CONFIRMED — function did not exit within 5s timeout; "
                        "spec B.6 requires immediate exit when spec_procs are all "
                        "done and not all expected files are ready, but the code "
                        "on line 209 waits for reasoning_futures to drain first "
                        "(extra guards: `not reasoning_futures and not validation_futures`)"
                    )
                else:
                    if result["exception"]:
                        print(
                            f"NOT CONFIRMED — function exited with error: "
                            f"{result['exception']}"
                        )
                    else:
                        print(
                            "NOT CONFIRMED — function exited within 5s timeout "
                            "(unexpected; the buggy guard should have kept it looping)"
                        )

    # ---- Stage 6: Cleanup ---------------------------------------------------
    shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
Functions pending verification: 2
CONFIRMED — function did not exit within 5s timeout; spec B.6 requires immediate exit when spec_procs are all done and not all expected files are ready, but the code on line 209 waits for reasoning_futures to drain first (extra guards: `not reasoning_futures and not validation_futures`)
```
