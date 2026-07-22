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
  - Return...

---

### Actual Behavior

validation_futures = (V0  S) \ Done, where S = {(vf, (fpath, rel_path, result_json_rel, completed_count))} if and only if verdict = "MISMATCH" and the assignment validation_futures[vf] = ... succeeded before any exception, otherwise S = . Done = { f | f  dom(V0  S)  f.done() }. All other variables (processed, submitted, reasoning_futures, completed_count, num_functions, executor, work_dir, proj_dir, resume, expected_files, poll_interval, spec_procs, ) retain their preblock values. No exception propagates out of the block; logs, file I/O, and print output may have occurred but do not affect the abstract state.

---

## Code Evidence

Line 133: `if _all_procs is not None and all(_spec_task_done(p) for p in _all_procs):`
Line 134: `unready = (expected_files or set()) - processed`
Line 135: `if unready and not reasoning_futures and not validation_futures:`

---

## Trigger Condition

The early exit condition triggered when all spec_procs have exited does not check whether the unprocessed expected files are actually ready (i.e., have the required markers). If files already contain the [SPEC] and [INFO] markers before any processing occurs, and the spec_procs list is empty or all processes have finished, the loop breaks prematurely, leaving ready files unsubmitted. This violates the requirement that every file whose is_file_ready() returns True must be submitted to _verify_single_file exactly once.

---

## How to trigger the bug

The early-exit guard at lines 205-226 of `src/verification.py` (in `streaming_reasoner`) checks whether all `spec_procs` have finished and whether there are unprocessed expected files with no in-flight futures, but it does **not** call `is_file_ready()` on the remaining files. If a file becomes ready (its markers are present) between the scan loop's `is_file_ready()` check and the early-exit evaluation — or if `is_file_ready()` previously returned `False` due to a timing gap but the file is now genuinely ready — the function breaks out of the loop without ever submitting that file for verification. The spec requires that every file for which `is_file_ready()` returns `True` must be submitted exactly once; the missing `is_file_ready()` re-check in the early-exit path violates this guarantee.

### Inputs

| Parameter | Value |
|-----------|-------|
| `input_dir` | Temp directory containing two `.py` files with valid `[SPEC]`/`[SPEC]`/`[INFO]`/`[INFO]` markers |
| `file_list` | `["ready_file.py", "ready_file2.py"]` |
| `spec_procs` | List containing one already-completed `concurrent.futures.Future` |
| `poll_interval` | `0.01` |

### Expected (spec-correct) Output

Both `ready_file.py` and `ready_file2.py` are submitted to `_verify_single_file` and their paths appear in the returned `processed` set.

### Actual (buggy) Output

No files are processed. The function prints the warning: `Spec generation process(es) exited (codes [0]) but no files received [SPEC]/[INFO] markers.` and returns an empty `processed` set. Both ready files are left unverified.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import sys, os, tempfile, json, concurrent.futures
from unittest.mock import patch

sys.path.insert(0, os.getcwd())

workspace = tempfile.mkdtemp()
input_dir = os.path.join(workspace, "input")
output_dir = os.path.join(workspace, "output")
proj_dir = os.path.join(workspace, "project")
os.makedirs(input_dir)
os.makedirs(output_dir)
os.makedirs(proj_dir)

# Create ready files with [SPEC]/[SPEC]/[INFO]/[INFO] markers
ready = "# [SPEC]\n# spec\n# [SPEC]\n# [INFO]\n# info\n# [INFO]\ndef f(): pass\n"
for name in ("ready_file.py", "ready_file2.py"):
    with open(os.path.join(input_dir, name), "w") as f:
        f.write(ready)

ex = concurrent.futures.ThreadPoolExecutor()
fut = ex.submit(lambda: 0); fut.result()  # already-done future

# Mock: first call to is_file_ready returns False (simulates scan not seeing
# the file as ready), subsequent calls return True (file IS actually ready)
calls = {}
def mock_is_ready(path):
    n = calls.get(path, 0)
    calls[path] = n + 1
    return n > 0

from src.verification import streaming_reasoner

with patch("src.verification.is_file_ready", side_effect=mock_is_ready), \
     patch("src.verification._verify_single_file") as mock_verify, \
     patch("src.verification._generate_validation_summary"), \
     patch("src.verification.MAX_WORKERS", 2):
    mock_verify.return_value = ("/fake/path", "MATCH")
    result = streaming_reasoner(
        input_dir=input_dir,
        output_dir=output_dir,
        file_list=["ready_file.py", "ready_file2.py"],
        proj_dir=proj_dir,
        work_dir=proj_dir,
        poll_interval=0.01,
        spec_procs=[fut],
    )

expected = {os.path.join(input_dir, r) for r in ["ready_file.py", "ready_file2.py"]}
assert expected <= result, f"BUG: expected {expected} but got {result}"
ex.shutdown(wait=False)
shutil.rmtree(workspace)
// actual (buggy) output: empty processed set, early-exit warning printed
// expected (correct) output: both files processed and verified
```

---

## Probe Script

```py
"""Probe script for bug: src--verification-py--streaming_reasoner"""

import sys
import os
import tempfile
import shutil
import json
import concurrent.futures
from unittest.mock import patch, MagicMock

# The streaming_reasoner and is_file_ready live in src.verification
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Simulate workspace path construction for the state files
_path_file = os.path.join(tempfile.gettempdir(), "fm_agent_state", "version.log")
os.makedirs(os.path.dirname(_path_file), exist_ok=True)
with open(_path_file, 'w') as f:
    f.write("dummy-commit-id")
toplevel_path = os.path.join(tempfile.gettempdir(), "fm_agent_state", "state.json")
with open(toplevel_path, 'w') as f:
    json.dump({"entry_func": None}, f)


def run_test():
    """Drive the bug reproduction."""
    from src.verification import streaming_reasoner

    # Create fresh temp workspace (NOT under fm_agent/)
    workspace = tempfile.mkdtemp(prefix="probe_workspace_")
    input_dir = os.path.join(workspace, "input")
    output_dir = os.path.join(workspace, "output")
    proj_dir = os.path.join(workspace, "project")
    os.makedirs(input_dir)
    os.makedirs(output_dir)
    os.makedirs(proj_dir)

    # Create a "ready" file — it has the required SPEC/SPEC/INFO/INFO markers
    ready_content = """# [SPEC]
# test spec
# [SPEC]
# [INFO]
# test info
# [INFO]
def example():
    pass
"""
    ready_path = os.path.join(input_dir, "ready_file.py")
    with open(ready_path, "w") as f:
        f.write(ready_content)

    # Create a second ready file
    ready_path2 = os.path.join(input_dir, "ready_file2.py")
    with open(ready_path2, "w") as f:
        f.write(ready_content)

    # file_list includes both files (relative paths from input_dir)
    file_list = ["ready_file.py", "ready_file2.py"]

    # spec_procs: already-finished futures so the early exit path triggers
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    done_future = ex.submit(lambda: 0)
    done_future.result()  # ensure it is done

    # Strategy:
    # 1. The real is_file_ready returns True for the files (they have markers).
    # 2. But if the scan loop finds them ready, they get submitted → no bug.
    # 3. The bug is: if a file becomes ready BETWEEN the scan and the early-exit
    #    check (or spec_procs finish), the early exit fires without re-checking.
    #
    # To trigger this deterministically: make is_file_ready return False on the
    # first call (simulating "not ready yet"), then True on subsequent calls.
    # The scan loop passes over the file as "not ready". The early exit fires.
    # The next scan would have picked it up but never gets to run.

    call_counts = {}

    def controlled_is_file_ready(file_path):
        count = call_counts.get(file_path, 0)
        call_counts[file_path] = count + 1
        if count == 0:
            # First call: pretend file is NOT ready
            return False
        # Subsequent calls: file IS ready
        return True

    # Mock _verify_single_file so we don't invoke LLMs or OpenCode
    def fake_verify(file_path, input_dir_arg, output_dir_arg, language, work_dir_arg, resume_arg):
        rel = os.path.relpath(file_path, input_dir_arg)
        out_path = os.path.join(output_dir_arg, os.path.splitext(rel)[0] + ".json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump({"function": file_path, "verdict": "MATCH", "gaps": None}, f)
        return (file_path, "MATCH")

    with patch("src.verification.is_file_ready", side_effect=controlled_is_file_ready), \
         patch("src.verification._verify_single_file", side_effect=fake_verify), \
         patch("src.verification._generate_validation_summary", return_value=None), \
         patch("src.verification.MAX_WORKERS", 2):

        result = streaming_reasoner(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=file_list,
            proj_dir=proj_dir,
            work_dir=proj_dir,
            poll_interval=0.01,
            spec_procs=[done_future],
            already_processed=None,
            resume=False,
        )

    ex.shutdown(wait=False)

    # ---------- Verdict ----------
    # Check whether all expected files are in the returned processed set.
    expected_files = {os.path.join(input_dir, rel) for rel in file_list}
    missing = expected_files - result

    if missing:
        # Bug reproduced: some expected files were never processed.
        rel_missing = [os.path.relpath(m, input_dir) for m in sorted(missing)]
        print(f"CONFIRMED — missed ready file(s): {rel_missing} | processed: {[os.path.relpath(p, input_dir) for p in sorted(result)]}")
    else:
        print(f"NOT CONFIRMED — all {len(file_list)} files processed: {[os.path.relpath(p, input_dir) for p in sorted(result)]}")

    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


try:
    run_test()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
Functions pending verification: 2
WARNING:root:Spec generation process(es) exited (codes [0]) but no files received [SPEC]/[INFO] markers.
CONFIRMED — missed ready file(s): ['ready_file.py', 'ready_file2.py'] | processed: []
```
