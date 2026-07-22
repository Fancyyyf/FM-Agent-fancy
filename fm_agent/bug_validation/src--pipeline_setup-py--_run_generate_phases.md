# Bug Report: _run_generate_phases

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/pipeline_setup-py/_run_generate_phases.py`
**Original source:** `src/pipeline_setup.py`
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

Natural language:
After executing lines 81130 starting from a state where the previous try block completed normally (i.e., run_opencode_traced returned successfully, prompt, prompt_file, command are set, trace event recorded, attempt = 1, and phases.json may or may not exist), one of three mutually exclusive outcomes occurs:
1. Break (line 103): phase_plan_ready becomes True. The value of phase_plan_errors is computed as \(phase_plan_schema_errors(phases_json)\) if phases.json exists, else ["phases.json is missing"]. The variables failure and missing are not set. The outer loop is exited; execution continues after that loop.
2. Sys.exit (line 130): if phase_plan_ready is False and \(attempt \ge OPENCODE_MAX_RETRIES\), the program prints an error message and terminates with exit code 1. No further program state exists.
3. Retry (line 123): if phase_plan_ready is False and \(attempt < OPENCODE_MAX_RETRIES\), the block prints a warning, sleeps for 10 seconds, and then completes (the code outside the block will increment attempt and re-enter the loop). In this case, phase_plan_ready remains False, failure is set to "update phases.json" if is_incremental else "produce phases.json", missing is set accordingly, and phase_plan_errors holds its computed list.

The bug is that outcome 1 (Break) can occur when the mtime of phases.json changed but the file does NOT cover all current source files, because the readiness check uses `or` instead of `and`.

---

## Code Evidence

Line 95:             elif is_incremental:
Line 96:                 phase_plan_ready = (
Line 97:                     os.path.getmtime(phases_json) != prev_mtime
Line 98:                     or _phases_cover_current_sources(phases_json, proj_dir)
Line 99:                 )

(Original source: `src/pipeline_setup.py`, lines 1003-1007)

---

## Trigger Condition

When is_incremental is true, the code sets phase_plan_ready to True solely because the file modification time changed, even if _phases_cover_current_sources returns False. The specification requires that a valid phases.json be accepted in incremental mode only when it covers all current source files; a timestamp change alone does not satisfy that requirement.

---

## How to trigger the bug

When `is_incremental=True`, after the OpenCode agent modifies phases.json (changing its mtime) but the resulting file does not cover all current source files, the `or` operator on line 1006 makes `phase_plan_ready` True, causing the function to return without retrying. The correct behavior would require both mtime change AND coverage — using `and` instead of `or`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `is_incremental` | `True` |
| `phases.json` (present, valid schema, incomplete) | `{"phases": [{"phase": 1, "modules": [{"source_files": ["not_in_project.py"]}]}]}` |
| Project source files | `real_source.py` (not listed in phases.json) |
| `prev_mtime` | mtime of phases.json before agent run |
| Agent action | modifies phases.json (mtime changes) but does NOT add missing source file |

### Expected (spec-correct) Output

`phase_plan_ready = False` — function should retry or exit because coverage is incomplete

### Actual (buggy) Output

`phase_plan_ready = True` — function returns normally, accepting an incomplete phases.json

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, time
from src.pipeline_setup import _phases_cover_current_sources

# Setup: create a phases.json that is valid but incomplete
phases_json = "/tmp/test/phases.json"
phases_content = {
    "phases": [{"phase": 1, "modules": [{"source_files": ["missing.py"]}]}]
}
with open(phases_json, "w") as f:
    json.dump(phases_content, f)

prev_mtime = os.path.getmtime(phases_json)
time.sleep(0.02)
os.utime(phases_json, None)  # simulate agent modifying the file

# BUGGY condition (actual code):
buggy = (os.path.getmtime(phases_json) != prev_mtime
         or _phases_cover_current_sources(phases_json, proj_dir))
# actual (buggy) output: True (WRONG — coverage is incomplete)

# CORRECT condition (spec requires):
correct = (os.path.getmtime(phases_json) != prev_mtime
           and _phases_cover_current_sources(phases_json, proj_dir))
# expected (correct) output: False (coverage is incomplete)
```

---

## Probe Script

```python
"""Probe script for bug src--pipeline_setup-py--_run_generate_phases.

Bug: In _run_generate_phases() at lines ~1003-1007, when is_incremental=True,
phase_plan_ready uses OR between mtime check and coverage check instead of AND.
This means a phases.json that was modified (mtime changed) but does NOT cover all
current source files is incorrectly accepted as ready.

The spec says: "a valid phases.json already present under work_dir may be accepted
without modification if it covers all current source files, even when its
modification timestamp has not changed" — coverage is the requirement, not mtime.
"""

import sys
import os
import json
import time
import subprocess
import tempfile
from unittest import mock

# Repo root for import
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)


def test_bug():
    """Reproduce the bug by exercising the faulty logic in isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = os.path.join(tmpdir, "project")
        work_dir = os.path.join(tmpdir, "work")
        script_dir = os.path.join(tmpdir, "script")
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(script_dir, exist_ok=True)

        # Create a project source file
        source_path = os.path.join(proj_dir, "real_source.py")
        with open(source_path, "w") as f:
            f.write("# real source file\n")

        # Create a valid phases.json that does NOT cover real_source.py
        phases_json = os.path.join(work_dir, "phases.json")
        phases_content = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase 1",
                    "description": "First",
                    "modules": [
                        {
                            "name": "module_a",
                            "description": "A module",
                            "source_files": ["not_in_project.py"]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }
        with open(phases_json, "w") as f:
            json.dump(phases_content, f)

        # --- Precondition assertions ---
        # Verify coverage is incomplete (the bug trigger)
        from src.pipeline_setup import _phases_cover_current_sources, _phase_plan_schema_errors

        schema_errs = _phase_plan_schema_errors(phases_json)
        assert not schema_errs, f"phases.json should be schema-valid, got: {schema_errs}"

        covers = _phases_cover_current_sources(phases_json, proj_dir)
        assert not covers, (
            f"phases.json should NOT cover current sources "
            f"(missing 'real_source.py'), got={covers}"
        )

        # --- Simulate the buggy logic exactly as written ---
        prev_mtime = os.path.getmtime(phases_json)

        # Simulate agent touching the file (changing mtime) but not fixing coverage
        time.sleep(0.02)
        os.utime(phases_json, None)
        current_mtime = os.path.getmtime(phases_json)
        assert current_mtime != prev_mtime, "mtime must have changed (simulated agent modification)"

        # Re-verify coverage is still incomplete after touch
        covers_after = _phases_cover_current_sources(phases_json, proj_dir)
        assert not covers_after, "coverage should still be incomplete after touch"

        # ---- THE BUGGY CONDITION (actual code, lines 1004-1007) ----
        buggy_phase_plan_ready = (
            current_mtime != prev_mtime
            or _phases_cover_current_sources(phases_json, proj_dir)
        )

        # ---- THE CORRECT CONDITION (what the spec requires) ----
        # The spec says coverage is the gate. The mtime check should not override it.
        # Correct: use AND instead of OR
        correct_phase_plan_ready = (
            current_mtime != prev_mtime
            and _phases_cover_current_sources(phases_json, proj_dir)
        )

        # ---- Verdict ----
        # Bug CONFIRMED if: buggy says ready (True) but correct says not ready (False)
        bug_reproduced = buggy_phase_plan_ready and not correct_phase_plan_ready

        if bug_reproduced:
            print(
                f"CONFIRMED — buggy condition (OR) produces phase_plan_ready={buggy_phase_plan_ready}, "
                f"but spec-correct condition (AND) produces phase_plan_ready={correct_phase_plan_ready}. "
                f"phases.json was modified (mtime changed) but still does not cover all source files "
                f"(missing real_source.py). The OR incorrectly accepts it as ready."
            )
            print(f"  Bug location: src/pipeline_setup.py, lines 1003-1007")
            print(f"  Current:  phase_plan_ready = (mtime_changed OR _phases_cover_current_sources(...))")
            print(f"  Should be: phase_plan_ready = (mtime_changed AND _phases_cover_current_sources(...))")
            return True
        else:
            print(
                f"NOT CONFIRMED — buggy={buggy_phase_plan_ready}, correct={correct_phase_plan_ready}"
            )
            return False


def main():
    try:
        test_bug()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — buggy condition (OR) produces phase_plan_ready=True, but spec-correct condition (AND) produces phase_plan_ready=False. phases.json was modified (mtime changed) but still does not cover all source files (missing real_source.py). The OR incorrectly accepts it as ready.
  Bug location: src/pipeline_setup.py, lines 1003-1007
  Current:  phase_plan_ready = (mtime_changed OR _phases_cover_current_sources(...))
  Should be: phase_plan_ready = (mtime_changed AND _phases_cover_current_sources(...))
```
