# Bug Report: streaming_reasoner

**Source file:** `src/verification-py/streaming_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a set of absolute paths consisting of every path in already_processed together with every file that completed verification during this invocation; no path present in already_processed is ever submitted for verification. The expected files are the file_list entries whose extension is a recognized source-language extension (or, when file_list is None, every file under input_dir with such an extension). Every expected file whose two sidecars are both schema-valid is picked up for verification without waiting for other files' sidecars, with readiness re-checked periodically; verifications of distinct files proceed concurrently with in-flight count bounded by the configured worker limit, and when spec_procs is given the whole invocation overlaps in time with in-flight spec generation. For each verified file a schema-valid verification result file exists under output_dir afterward, except that a function with no usable spec text yields no result file and is counted as processed with a SKIPPED outcome. Only MISMATCH verdicts trigger bug validation; when proj_dir is provided, every MISMATCH is submitted to bug validation before return. The invocation returns only after every verification and bug validation it submitted has completed. While all spec handles have terminated but expected files remain unready and nothing is in flight, the watcher exits early, reports each unready file as pending for caller-side retry, and raises no error. Whenever proj_dir is provided, after the watch loop ends by any path, including user interruption, the aggregate validation summary over the bug-validation results in work_dir is generated or refreshed. Extracted function source files and their sidecar files are never modified.

---

### Actual Behavior

Upon completion of the code block (lines 121187), the following state holds across all execution paths:

=== SECTION 1: Validation-result processing (lines 121137), for each future in val_done ===

For each completed validation future iterated in val_done:

S1a. PREFIX STRIPPING (lines 121123):
  Let prefix_sep = os.path.join("fm_agent", "logic_verification_results") + os.sep.
  Let prefix_fwd = "fm_agent/logic_verification_results/".
  (i) If parts.startswith(prefix_sep) was True (line 120 condition):
      parts' = parts[len(prefix_sep):]  (line 121)
  (ii) Elif parts.startswith(prefix_fwd) (line 122):
      parts' = parts[len(prefix_fwd):]  (line 123)
  (iii) Else: parts is unchanged.

S1b. BUG ID AND RESULT PATH (lines 124125):
  bug_id == os.path.splitext(parts')[0].replace(os.sep, "--").replace("/", "--")
  result_path == os.path.join(work_dir, "bug_validation", f"{bug_id}.result.json")

S1c. CONFIRMATION CHECK (lines 126130):
  confirmed == False initially.
  If os.path.exists(result_path) is True:
    result_data == json.load(open(result_path))
    confirmed == (result_data.get("confirmation_status") == "confirmed")
  If os.path.exists(result_path) is False:
    confirmed remains False.

S1d. STDOUT OUTPUT (lines 131134):
  If confirmed is True:
    stdout receives '[{count}/{num_functions}] {rel_path}: \033[31m\033[0m'
  Else:
    stdout receives '[{count}/{num_functions}] {rel_path}: \033[32m\033[0m'

S1e. LOGGING (line 135):
  An INFO-level log entry 'Validation completed: {fpath} (confirmed={confirmed})' is emitted.

S1f. EXCEPTION DURING VALIDATION PROCESSING (lines 136137):
  If any exception exc is raised within lines 115135 (including future.result(), file I/O, json.load, etc.):
    An ERROR-level log entry 'Validation error for {fpath}: {exc}' is emitted.
    No stdout verdict line is printed for this future.
    Execution continues to the next iteration or past the for-loop.

S1g. validation_futures is updated: each completed future is removed.
  validation_futures' = validation_futures \ val_done (all completed futures popped).

=== SECTION 2: Loop-termination checks (lines 139169) ===

S2a. ALL-REASONING-DONE CHECK (lines 139146):
  all_reasoning_done == (expected_files is not None AND processed >= expected_files AND not reasoning_futures).
  If all_reasoning_done is True AND validation_futures is empty:
    An INFO-level log 'All files verified and validated. Done.' is emitted.
    The while True loop is exited via break.
    Execution proceeds to line 185.

S2b. SPEC-PROCESS-EXIT CHECK (lines 148168):
  _all_procs == spec_procs if spec_procs else None.
  If _all_procs is not None AND all(_spec_task_done(p) for p in _all_procs) is True:
    unready == (expected_files or set()) - processed.
    If unready is non-empty AND reasoning_futures is empty AND validation_futures is empty:
      exit_codes == [_spec_task_exit_code(p) for p in _all_procs].
      If processed is empty:
        A WARNING log about no sidecar pairs created is emitted.
      Else:
        A WARNING log about {len(unready)} files missing specs is emitted.
        For each uf in sorted(unready):
          rel_path_local == os.path.relpath(uf, proj_dir) if proj_dir else os.path.relpath(uf, input_dir)
          stdout receives '[pending] {rel_path_local}: no spec yet; will retry'
      The while True loop is exited via break.
      Execution proceeds to line 185.

S2c. POLLING SLEEP (line 169):
  If neither break condition is met, time.sleep(poll_interval) is called and the while loop iterates again.
  (In this case the code block does not terminate at line 187 in this iteration; the post-condition applies to the eventual exit.)

=== SECTION 3: KeyboardInterrupt handler (lines 170183) ===

If a KeyboardInterrupt is raised during the while True loop:
S3a. An INFO-level log 'Stopping watcher...' is emitted.
S3b. all_futures == reasoning_futures  validation_futures (merged dict).
S3c. For each future in all_futures:
  fpath_k == all_futures[future].
  future.result() is called.
  On success: INFO log 'Completed: {fpath_k}'.
  On exception exc_k: ERROR log 'Error for {fpath_k}: {exc_k}'.
S3d. An INFO-level log 'Done.' is emitted.
S3e. Execution proceeds to line 185.

=== SECTION 4: Post-loop finalization (lines 185187) ===

S4a. If proj_dir is not None:
  _generate_validation_summary(work_dir) is called.
  Post: work_dir/bug_validation/summary.json exists with keys 'total_reported', 'total_confirmed', 'total_not_confirmed', 'total_error' and a 'bugs' list ordered by status group then bug_id. Written atomically. No bug report files are modified.
S4b. If proj_dir is None:
  _generate_validation_summary is NOT called.
S4c. The function returns processed (the set of all file paths that were successfully processed).

=== GLOBAL INVARIANTS ===

G1. No file under input_dir is created, modified, or deleted.
G2. The ThreadPoolExecutor may or may not still be active (it is not explicitly shut down in this block, but the loop has exited).
G3. The return value is the set `processed`.
G4. fpath  submitted (removed earlier); fpath  processed (on Path A).
G5. All futures in reasoning_futures at loop exit map to file paths not in processed.
G6. processed'  processed  {fpath} (from Path A pre-condition).
G7. completed_count' == 1 (on Path A).
G8. The while True loop has terminated (via break at line 146, break at line 168, or KeyboardInterrupt at line 170).

=== FORMAL LOGIC ===

Let RET denote the return value.

RET == processed'

processed'  processed  {fpath}

fpath  submitted'

(proj_dir  None)   summary_file: summary_file == os.path.join(work_dir, "bug_validation", "summary.json")  os.path.exists(summary_file)

 fp  input_dir tree: file_content(fp) is unchanged

 vf  validation_futures at loop entry: vf is resolved (result retrieved or error logged) before loop exit

(loop_exit_reason  {"all_done", "spec_procs_exited", "keyboard_interrupt"})

(loop_exit_reason == "all_done")  (expected_files  None  processed'  expected_files  reasoning_futures == {}  validation_futures == {})

(loop_exit_reason == "spec_procs_exited")  (spec_procs  None   p  spec_procs: _spec_task_done(p)   unready  expected_files: unready  processed' ==   reasoning_futures == {}  validation_futures == {})

(loop_exit_reason == "keyboard_interrupt")  ( f  reasoning_futures  validation_futures: f.result() was called)

No unhandled exception propagates past line 187.

---

## Code Evidence

Line 176: for future in all_futures:
Line 177: fpath = all_futures[future]
Line 178: try:
Line 179: future.result()
Line 180: logging.info(f"Completed: {fpath}")

---

## Trigger Condition

The specification requires 'when proj_dir is provided, every MISMATCH is submitted to bug validation before return.' In the KeyboardInterrupt handler (lines 176-180), the code calls future.result() for each in-flight future but discards the returned verdict. If a reasoning future resolves with a MISMATCH verdict during interrupt handling, the code logs 'Completed' without submitting bug validation. Since proj_dir is provided, the spec mandates that this MISMATCH be submitted to bug validation before the function returns. The handler only waits for already-submitted work to finish but never inspects the verdict to trigger new bug-validation submissions, violating the absolute 'every MISMATCH is submitted' requirement.

---

## How to trigger the bug

`streaming_reasoner` (implemented in `src/verification.py`, lines 64-265) is
called with `proj_dir` provided and a single expected file whose verification
resolves with a `MISMATCH` verdict. While that reasoning future is still
in flight, the watch loop is interrupted (a `KeyboardInterrupt` is raised at
the loop's first `time.sleep`, simulating user interruption). Control reaches
the `except KeyboardInterrupt` handler (`src/verification.py:246-259`), which
drains every in-flight future via `future.result()` but **discards the
returned `(file_path, verdict)` tuple**. Because the verdict is never
inspected on this path, the MISMATCH is never submitted to
`_validate_single_bug`, violating the spec clause "when proj_dir is provided,
every MISMATCH is submitted to bug validation before return" (the spec holds
this for every exit path, including user interruption).

### Inputs

| Parameter | Value |
|-----------|-------|
| `input_dir` | `<tmp>/extracted_functions` containing one ready file `victim.py` (fresh temp dir owned by the probe) |
| `output_dir` | `<tmp>/logic_verification_results` |
| `file_list` | `["victim.py"]` |
| `proj_dir` | provided (`<tmp>`) |
| `work_dir` | `<tmp>` |
| `poll_interval` | `0.05` |
| mocked `is_file_ready` | always `True` (both sidecars ready) |
| mocked `_verify_single_file` | in flight for 0.4s, then returns `(file_path, "MISMATCH")` |
| interrupt | `KeyboardInterrupt` raised by the loop's first `time.sleep` while the reasoning future is in flight |

### Expected (spec-correct) Output

`>= 1` bug-validation submission (`_validate_single_bug` invoked for the
MISMATCH result) before `streaming_reasoner` returns, even on the
interrupt path.

### Actual (buggy) Output

`0` bug-validation submissions: the `KeyboardInterrupt` handler calls
`future.result()`, logs `Completed: <path>`, discards the `MISMATCH` verdict,
and returns without ever calling `_validate_single_bug`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the probe (uses the package entry point `import src.verification`,
   mocks all collaborators, and never starts an FM-Agent workflow):

```bash
python3 fm_agent/bug_validation/probe_src--verification-py--streaming_reasoner.py
# actual (buggy) output:  bug_validation_submissions=0  -> CONFIRMED
# expected (correct) output:  bug_validation_submissions>=1 (every MISMATCH submitted)
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for bug `src--verification-py--streaming_reasoner`.

Spec claim (relevant excerpt):
  "Only MISMATCH verdicts trigger bug validation; when proj_dir is provided,
   every MISMATCH is submitted to bug validation before return."
  and the summary must be generated "after the watch loop ends by any path,
   including user interruption".

Reported bug:
  In the KeyboardInterrupt handler of streaming_reasoner()
  (src/verification.py, ~lines 246-259), the code waits for the in-flight
  futures via future.result() but discards the returned verdict. A reasoning
  future that resolves with a MISMATCH verdict during interrupt handling is
  therefore never submitted to _validate_single_bug(), violating the absolute
  "every MISMATCH is submitted" requirement.

Strategy (deterministic, no FM-Agent workflow started):
  1. Fresh temp-dir fixture with one ready source file declared via file_list.
  2. Patch module-level collaborators of streaming_reasoner():
       - is_file_ready                -> always True
       - _verify_single_file          -> sleeps briefly (stays in flight),
                                         then returns (path, "MISMATCH")
       - _validate_single_bug         -> records the call, does nothing
       - _generate_validation_summary -> records the call, does nothing
       - time (module attribute)      -> shim whose sleep() raises
                                         KeyboardInterrupt on the loop's first
                                         poll, while the reasoning future is
                                         still in flight
  3. Call streaming_reasoner() with proj_dir provided.
  4. Oracle: the reasoning future resolved with MISMATCH, but
     _validate_single_bug was never called -> the interrupt path dropped a
     MISMATCH without submitting bug validation -> CONFIRMED.

FM-Agent self-validation guard compliance: this probe never starts an
FM-Agent workflow (no run_pipeline(), run_incremental_pipeline(), main.py,
FM-Agent CLI, OpenCode, or any FM-Agent subprocess). It unit-tests only
src.verification.streaming_reasoner with mocks, and every fixture/runtime
file lives under a fresh temporary directory owned by the probe.
"""

import os
import shutil
import sys
import tempfile
import time as real_time

# Resolve the repo root (probe lives in fm_agent/bug_validation/) so the
# package import works regardless of the caller's cwd.
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Load the package via its package namespace (public entry point).
import src.verification as V  # noqa: E402


def main():
    tmp = tempfile.mkdtemp(prefix="probe_streaming_reasoner_")
    input_dir = os.path.join(tmp, "extracted_functions")
    output_dir = os.path.join(tmp, "logic_verification_results")
    proj_dir = tmp  # proj_dir is provided => every MISMATCH must be submitted
    work_dir = tmp
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    victim_rel = "victim.py"
    victim_path = os.path.join(input_dir, victim_rel)
    with open(victim_path, "w", encoding="utf-8") as fh:
        fh.write("def victim():\n    return 42\n")

    calls = {"verify": [], "validate": [], "summary": []}
    verdict_holder = {}

    def fake_verify(file_path, in_dir, out_dir, language, work_dir=None, resume=False):
        # Simulate a verification that is still in flight when the interrupt
        # arrives, then resolves with a MISMATCH verdict.
        real_time.sleep(0.4)
        verdict_holder["verdict"] = "MISMATCH"
        calls["verify"].append(file_path)
        return file_path, "MISMATCH"

    def fake_validate(result_json_rel, proj_dir_arg, work_dir_arg=None,
                      resume=False, bug_validator_path=None):
        calls["validate"].append(result_json_rel)
        return result_json_rel

    def fake_summary(dir_arg):
        calls["summary"].append(dir_arg)

    class FakeTime:
        """Raises KeyboardInterrupt on the watch loop's first poll."""

        def __init__(self):
            self.sleep_calls = 0

        def sleep(self, seconds):
            self.sleep_calls += 1
            raise KeyboardInterrupt()

        def __getattr__(self, name):
            return getattr(real_time, name)

    originals = {
        "is_file_ready": V.is_file_ready,
        "_verify_single_file": V._verify_single_file,
        "_validate_single_bug": V._validate_single_bug,
        "_generate_validation_summary": V._generate_validation_summary,
        "time": V.time,
    }

    crashed = None
    try:
        V.is_file_ready = lambda path: True
        V._verify_single_file = fake_verify
        V._validate_single_bug = fake_validate
        V._generate_validation_summary = fake_summary
        V.time = FakeTime()

        V.streaming_reasoner(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=[victim_rel],
            proj_dir=proj_dir,
            work_dir=work_dir,
            poll_interval=0.05,
            spec_procs=None,
            already_processed=None,
            resume=False,
            bug_validator_path=None,
        )
    except KeyboardInterrupt:
        crashed = "KeyboardInterrupt escaped streaming_reasoner (unexpected)"
    except Exception as exc:  # noqa: BLE001
        crashed = f"{type(exc).__name__}: {exc}"
    finally:
        for name, value in originals.items():
            setattr(V, name, value)

    if crashed is not None:
        print(f"ERROR: {crashed}")
        sys.exit(1)

    verdict = verdict_holder.get("verdict")
    n_verify = len(calls["verify"])
    n_validate = len(calls["validate"])

    detail = (
        f"verdict={verdict!r} | verify_calls={n_verify} | "
        f"bug_validation_submissions={n_validate} | proj_dir=provided | "
        f"expected_submissions>=1"
    )

    if verdict == "MISMATCH" and n_verify == 1 and n_validate == 0:
        # The reasoning future resolved with MISMATCH during interrupt
        # handling, yet no bug validation was ever submitted.
        print(
            "CONFIRMED - MISMATCH resolved during interrupt handling was never "
            f"submitted to bug validation ({detail}); spec requires every "
            "MISMATCH to be submitted to bug validation before return when "
            "proj_dir is provided"
        )
    elif n_validate >= 1:
        print(
            "NOT CONFIRMED - every MISMATCH was submitted to bug validation "
            f"as the spec requires ({detail})"
        )
    else:
        print(
            "NOT CONFIRMED - scenario did not produce the expected "
            f"in-flight MISMATCH state ({detail})"
        )

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)

```

### Probe Output

```
Functions pending verification: 1
CONFIRMED - MISMATCH resolved during interrupt handling was never submitted to bug validation (verdict='MISMATCH' | verify_calls=1 | bug_validation_submissions=0 | proj_dir=provided | expected_submissions>=1); spec requires every MISMATCH to be submitted to bug validation before return when proj_dir is provided
```
