# Bug Report: _run_generate_phases

**Source file:** `src/pipeline_setup-py/_run_generate_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- On normal return: phases.json exists under work_dir and conforms to the phases.json schema
- When resume is truthy and phases.json already satisfies the pipeline's completeness criteria, the function returns without producing or modifying any file
- When submodules is provided: phases.json covers all source files under the specified subdirectories of proj_dir; source files outside those subdirectories are neither added nor required to be present
- When is_incremental is truthy: a valid phases.json already present under work_dir may be accepted without modification if it covers all current source files, even when its modification timestamp has not changed
- If valid phases.json is not produced or confirmed after a configurable maximum number of retry attempts, the function prints a diagnostic message to stdout identifying the failed stage and the trace directory, then calls sys.exit(1)
- When a non-final attempt fails to produce valid phases.json, the function does not call sys.exit(1)  it waits a fixed interval before retrying

---

### Actual Behavior

After the code block finishes, the original input parameters (`proj_dir`, `work_dir`, `script_dir`, `is_incremental`, `resume`, `submodules`) remain unchanged. The file `workflow_generate_phases.md` and any staged domain knowledge files are unmodified. One of the following mutually exclusive outcomes holds:

1. **Phase plan ready (break):** A `break` statement has been executed, exiting the enclosing retry loop. The variable `phase_plan_ready` is `True`, and the file `phases.json` exists under `work_dir/fm_agent/`. Depending on the configuration:
   - If `submodules` is not `None`, every source file under the specified subdirectories is referenced in `phases.json`.
   - If `is_incremental` is `True` and `submodules` is `None`, either the modification time of `phases.json` differs from `prev_mtime` or all source files in `proj_dir` are referenced in `phases.json`.
   - Otherwise (`submodules` is `None` and `is_incremental` is `False`), `phases.json` is a valid JSON file.

2. **Retry (continue loop):** No `break` occurred, `attempt < OPENCODE_MAX_RETRIES`, and the program has printed a retry message (`[Pipeline] Stage 1 failed to ... Retrying in 10s...`) to stdout, logged a warning, and slept for 10 seconds. The variable `phase_plan_ready` is either not defined or `False`, and the program will proceed to the next iteration of the retry loop (with `attempt` incremented by the loop control). The file `phases.json` either does not exist or does not satisfy the required readiness condition.

3. **Fatal error (exit):** `attempt >= OPENCODE_MAX_RETRIES`, no `break` occurred, and `sys.exit(1)` has been called. An error message (`[Pipeline] ERROR: Stage 1 failed after ...`) was printed to stdout. The program terminates with exit code 1.

In all paths, if the subprocess executed by `run_opencode_traced` raised `subprocess.CalledProcessError`, the error was caught and logged; the program did not propagate it.

**Formal logic:**
Let `old(Var)` denote the value before the block, `exists(p)` denote `os.path.exists(p)`, `mtime(p)` the modification time, `prev_mtime` the prior mtime. Define predicate `Ready(p)` as:
```
Ready(p)  exists(p) 
  (submodules  None  _phases_cover_current_sources(p, proj_dir, submodules)) 
  (submodules = None  is_incremental  (mtime(p)  prev_mtime  _phases_cover_current_sources(p, proj_dir))) 
  (submodules = None  is_incremental  _json_file_is_valid(p) = True)
```
Post-condition ():
```
 (proj_dir = old(proj_dir)  work_dir = old(work_dir)  script_dir = old(script_dir)  is_incremental = old(is_incremental)  resume = old(resume)  submodules = old(submodules))
  (if break then (phase_plan_ready = True  Ready(phases_json)))
  (if break  attempt < OPENCODE_MAX_RETRIES then 
      (retry_msg_printed  logged_warning  slept(10)  (phase_plan_ready = True)))
  (if break  attempt  OPENCODE_MAX_RETRIES then (error_msg_printed  program_exit(1)))
  (if CalledProcessError raised then caught_and_logged else True)
```

---

## Code Evidence

Line 77:                 phase_plan_ready = _json_file_is_valid(phases_json)
Line 78:             if phase_plan_ready:
Line 79:                 break

---

## Trigger Condition

The code only verifies that phases.json contains valid JSON, not that it conforms to the required schema. The specification requires that on normal return phases.json 'conforms to the phases.json schema'. A valid JSON file that lacks required fields or uses an incorrect structure still passes _json_file_is_valid, making it possible to exit the retry loop with an invalid plan, violating the spec.

---

## How to trigger the bug

The bug lies in the else-branch at line 922 of `src/pipeline_setup.py` (within `_run_generate_phases`). When neither `submodules` nor `is_incremental` is truthy, the validation calls `_json_file_is_valid(phases_json)`. This function (defined in `src/file_utils.py`, line 112) only attempts `json.load()` — it returns True for any file containing valid JSON, regardless of whether the JSON conforms to the phases.json schema.

A valid phases.json must contain a `"phases"` array where each phase has `"phase"`, `"name"`, `"modules"`, and `"depends_on_phases"` fields, and each module has `"source_files"`. A file containing only `{}` (an empty JSON object) is valid JSON but does NOT conform to this schema — yet `_json_file_is_valid` returns True for it.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` (file content) | `{}` |

### Expected (spec-correct) Output

`_json_file_is_valid` should return `False` for `{}` because it does not conform to the phases.json schema (missing required `"phases"` key and nested structure).

### Actual (buggy) Output

`_json_file_is_valid` returns `True` for `{}` because it only validates that the file contains valid JSON, not that it conforms to the required schema.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _json_file_is_valid
import tempfile, json, os

tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
try:
    json.dump({}, tf)
    tf.close()
    is_valid = _json_file_is_valid(tf.name)  # returns True — BUG
    # actual (buggy) output: True
    # expected (correct) output: False ({} does not conform to phases.json schema)
finally:
    os.unlink(tf.name)
```

---

## Probe Script

```python
import sys
import os
import tempfile
import json

# The project uses src/ as its package root; import via the public module path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.file_utils import _json_file_is_valid

# The spec requires that phases.json "conforms to the phases.json schema"
# (must contain a "phases" array with structured phase/module entries).
# _json_file_is_valid only checks that the file is valid JSON — it does
# NOT validate schema conformance.  A file containing "{}" is valid JSON
# but is NOT a valid phases.json document.

tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
try:
    # Write an empty JSON object: valid JSON, but NOT a valid phases.json schema.
    json.dump({}, tf)
    tf.close()

    is_valid = _json_file_is_valid(tf.name)

    # Bug: _json_file_is_valid returns True for any valid JSON, regardless
    # of schema.  The spec requires schema conformance, which {} breaks.
    # passed=True → bug reproduced (invalid schema passes validation).
    passed = is_valid

    if passed:
        print(
            "CONFIRMED — _json_file_is_valid returned True for '{}' "
            "(valid JSON but does NOT conform to phases.json schema)"
        )
    else:
        print(f"NOT CONFIRMED — _json_file_is_valid returned {is_valid!r}")
finally:
    os.unlink(tf.name)
```

### Probe Output

```
CONFIRMED — _json_file_is_valid returned True for '{}' (valid JSON but does NOT conform to phases.json schema)
```
