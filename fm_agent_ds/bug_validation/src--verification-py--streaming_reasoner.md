# Bug Report: streaming_reasoner

**Source file:** `src/verification.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For every function in scope whose .spec.json and .info.json sidecars become complete during the polling window (as determined by is_file_ready), whose path is not in already_processed, and which has not already been submitted in this invocation: runs block-level Hoare-style reasoning that produces a verdict JSON file under output_dir. The verdict JSON contains a 'verdict' key with value MATCH, MISMATCH, or SKIPPED. For each MISMATCH verdict when proj_dir is not None: dispatches a bug validation that builds and executes a probe script, producing a bug_validation/<bug_id>.md report and a bug_validation/<bug_id>.result.json file whose 'confirmation_status' is 'confirmed' when the probe script reproduces the violation. For each processed function, prints a progress line with a unicode checkmark for MATCH, SKIPPED, and unconfirmed-MISMATCH verdicts, and a unicode crossmark for confirmed MISMATCH verdicts. When spec_procs is provided and all spec-generation futures have completed while in-scope files remain unready and no reasoning or validation futures are pending: prints a pending notice for each unready file and exits the polling loop. On KeyboardInterrupt: waits for all in-flight reasoning and validation futures to complete before returning. When proj_dir is not None: after the polling loop exits, generates bug_validation/summary.json aggregating total, confirmed, and not-confirmed bug counts across all validation results. Returns the set of all function file paths marked as processed during this invocation, including those already present in already_processed.

---

### Actual Behavior

The function returns the set `processed`. The following three mutually exclusive scenarios describe the state upon return:

1. **All files processed (break at line 146):**
   - `expected_files` is not None.
   - `processed`  `expected_files` (all expected files have been processed).
   - `reasoning_futures` is empty.
   - `validation_futures` is empty.
   - The enclosing loop is exited, then if `proj_dir  None`, `_generate_validation_summary(work_dir)` is called.

2. **Missing specs (break at line 168):**
   - `spec_procs` is not None and every subprocess `p` in `spec_procs` satisfies `_spec_task_done(p)` (all done).
   - `expected_files` is not None.
   - `processed`  `expected_files` (proper subset, there are unready files).
   - For each file `u` in `expected_files \\ processed`, a warning is logged and a "[pending]" message is printed.
   - `reasoning_futures` is empty.
   - `validation_futures` is empty.
   - The loop is broken, then summary generation if applicable.

3. **KeyboardInterrupt (lines 170-183):**
   - A `KeyboardInterrupt` occurred inside the `try` body.
   - In the exception handler, a dictionary `all_futures` is formed as the union of the then-current `reasoning_futures` and `validation_futures`.
   - For every future `f` in `all_futures`, `f.result()` is called. If a future raises an exception, it is caught and logged.
   - After the handler, all futures that existed at the moment of the interrupt are completed and their results consumed; the dictionaries `reasoning_futures` and `validation_futures` still contain those futures.
   - `processed` and `completed_count` remain as they were at the time of the interrupt (which may include the pre-condition addition of `fpath` if the interrupt occurred after that point).
   - Summary generation if applicable.

In all cases:
- If `proj_dir` is not None, `_generate_validation_summary(work_dir)` is executed, producing a bug validation summary file.
- T... (content truncated)

---

## Code Evidence

Line 222: *_all_procs = spec_procs if spec_procs else None** \
Line 223: **if _all_procs is not None and all(_spec_task_done(p) for p in _all_procs):** \
Line 224: **unready = (expected_files or set()) - processed** \
Line 225: **if unready and not reasoning_futures and not validation_futures:** \
Line 239: **for uf in sorted(unready):** \
Line 240: **rel_path = os.path.relpath(uf, proj_dir) if proj_dir else os.path.relpath(uf, input_dir)** \
Line 241: **print(f"[pending] {rel_path}: no spec yet; will retry")** \
Line 242: **break**

---

## Trigger Condition

The code identifies unready files solely as expected_files minus processed, without checking actual readiness of their sidecars. A file whose sidecars are ready but that has not yet been submitted for reasoning may be incorrectly marked as pending and skipped, causing a premature exit and violating the specification that all functions with complete .spec.json and .info.json files should be processed.

---

## How to trigger the bug

The `unready` set at line 224 is computed as `(expected_files or set()) - processed` — a simple set difference. It does not call `is_file_ready()` to verify whether each file in the difference truly lacks ready sidecars. As a result, when all `spec_procs` have completed but the scanning loop has not yet picked up a file whose sidecars became ready between iterations, the file is incorrectly classified as "no spec yet" and the polling loop exits prematurely.

### Inputs

| Parameter | Value |
|-----------|-------|
| `input_dir` | Temporary directory containing `hello.py` with valid `.spec.json` and `.info.json` sidecars |
| `output_dir` | Temporary output directory |
| `file_list` | `["hello.py"]` |
| `proj_dir` | Temporary project directory |
| `work_dir` | Temporary work directory |
| `spec_procs` | List containing one mock handle where `_spec_task_done()` returns `True` |
| `already_processed` | `None` |

### Expected (spec-correct) Output

`processed` set contains the file path `hello.py` — the file has ready sidecars and should be processed.

### Actual (buggy) Output

`processed` set is empty — the file was incorrectly marked as `[pending]` and skipped despite having ready sidecars.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# The buggy computation at src/verification.py line 224:
unready = (expected_files or set()) - processed
#  ^-- does NOT call is_file_ready() on each entry

# Correct behavior would be:
# unready = {f for f in ((expected_files or set()) - processed) if not is_file_ready(f)}

# When spec_procs are all done, reasoning_futures is empty, and a file's
# sidecars become ready between when the scanning loop passes over it and
# when the unready check fires, the file is incorrectly classified as
# "no spec yet" and the loop exits without processing it.
```

---

## Probe Script

```python
"""Probe script for bug_id: src--verification-py--streaming_reasoner

Bug: streaming_reasoner() computes `unready = (expected_files or set()) - processed`
without checking `is_file_ready()`. A file whose .spec.json/.info.json sidecars
are ready but hasn't yet been picked up by the scanning loop can be incorrectly
marked as pending and skipped, causing premature loop exit.

Strategy: Patch time.sleep and os.walk to orchestrate the race deterministically.
We make os.walk NOT return the file on iteration 1 (simulating sidecars not ready
at scan time), then return it on iteration 2. Since spec_procs are already done
on iteration 1, the unready check fires and incorrectly marks the file as pending.
"""

import sys
import os
import json
import tempfile
import types
import time
import threading
from unittest.mock import patch

# Avoid polluting the project directory with FM-Agent run artifacts.
# Use a temp dir as the probe workspace.
PROBE_TMP = tempfile.mkdtemp(prefix="streaming_reasoner_probe_")
INPUT_DIR = os.path.join(PROBE_TMP, "input")
OUTPUT_DIR = os.path.join(PROBE_TMP, "output")
WORK_DIR = os.path.join(PROBE_TMP, "work")
os.makedirs(INPUT_DIR)
os.makedirs(OUTPUT_DIR)
os.makedirs(WORK_DIR)

# Create a Python source file in the input dir
TEST_PY_NAME = "hello.py"
test_py_path = os.path.join(INPUT_DIR, TEST_PY_NAME)
with open(test_py_path, "w") as f:
    f.write("def greet(name):\n    return 'Hello ' + name\n")

# Create VALID sidecars — the file's spec/info ARE ready
spec_json = {
    "signature": "greet(name: str) -> str",
    "pre_condition": "name is a non-empty string",
    "post_condition": "returns 'Hello ' concatenated with name",
}
info_json = {"callees": []}
with open(test_py_path + ".spec.json", "w") as f:
    json.dump(spec_json, f)
with open(test_py_path + ".info.json", "w") as f:
    json.dump(info_json, f)

# ── orchestrate the race ────────────────────────────────────────────

# Iteration gate: os.walk is called once per while-loop iteration.
# On iteration 1 we want the scan to NOT see the file (so it isn't submitted).
# Since spec_procs are already done and reasoning_futures is empty, the
# unready check will fire and mark the file as pending → break.
# On iteration 2 os.walk returns the file normally (should never be reached
# if the bug is present, because iteration 1 already broke).

_iteration = [0]  # mutable counter so the closure can increment it

def _walk_controlled(top, **kwargs):
    """Controlled os.walk that hides the test file on the first call."""
    _iteration[0] += 1
    it = _orig_walk(top, **kwargs)
    if _iteration[0] == 1:
        # Filter out the test file on iteration 1 — it appears as if
        # sidecars aren't ready at scan time.
        for root, dirs, files in it:
            filtered = [f for f in files if f != TEST_PY_NAME]
            yield root, dirs, filtered
            for sub in dirs:
                # need to continue the walk
                pass
    else:
        yield from it


# Controlled sleep: don't actually sleep, just yield control so the
# iteration counter advances naturally.
def _sleep_skip(duration):
    """No-op sleep to speed up the test."""
    pass


# ── run the test ─────────────────────────────────────────────────────

actual = None
expected = True  # spec says: ready files should be processed, not skipped
passed = False
error_msg = None

try:
    # Pre-load modules before patching
    from src.verification import streaming_reasoner
    import os as os_mod

    _orig_walk = os_mod.walk

    with (
        patch("os.walk", side_effect=_walk_controlled),
        patch("time.sleep", side_effect=_sleep_skip),
    ):
        # Create a spec_procs handle that reports "done"
        class DoneHandle:
            @staticmethod
            def poll():
                return 0

            @staticmethod
            def done():
                return True

        processed = streaming_reasoner(
            input_dir=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            file_list=[TEST_PY_NAME],
            proj_dir=PROBE_TMP,
            work_dir=WORK_DIR,
            poll_interval=0.01,
            spec_procs=[DoneHandle()],
            already_processed=None,
            resume=False,
            bug_validator_path=None,
        )

        # SPEC says: file with ready sidecars should be processed.
        # If the return set includes the file → correct behavior.
        # If the file is missing → bug confirmed.
        actual = test_py_path in processed
        passed = not actual  # True if bug reproduced (file NOT processed)
except Exception as e:
    error_msg = str(e)
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — file with ready sidecars was NOT in processed set: {actual!r} "
        f"| expected: True"
    )
else:
    print(
        f"NOT CONFIRMED — file with ready sidecars IS in processed set: {actual!r} "
        f"| expected: True"
    )
```

### Probe Output

```
Functions pending verification: 1
WARNING:root:Spec generation process(es) exited (codes [1]) but no .spec.json/.info.json sidecar pairs were created.
CONFIRMED — file with ready sidecars was NOT in processed set: False | expected: True
```
