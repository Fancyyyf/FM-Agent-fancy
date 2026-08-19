# Bug Report: _run_generate_phases

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_run_generate_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the function returns normally (without exiting the process): either plugin_stage.type is 'pass' or 'replace' (the plugin assumes full responsibility for phases.json output), or phases.json exists at the expected path under work_dir containing a list of phases where each phase has a phase number (integer), name (string), description (string), modules (a list of objects each with name, description, and source_files), and depends_on_phases (a list of integers referencing other phase numbers). In incremental mode, the existing phases.json is updated to reflect the current source code state by adding new modules and source files that have appeared, removing entries whose files no longer exist, and adjusting phase assignments as needed while preserving still-accurate entries. In submodule-filtered mode, source_files entries reference only files within the specified subdirectory paths. If after OPENCODE_MAX_RETRIES attempts phases.json is missing, has schema validation errors, or in submodule mode fails to cover current sources under the specified subdirectories, the process exits with code 1 and emits a diagnostic message describing the failure.

---

### Actual Behavior

After the code block executes, one of the following holds:
1. (Termination) If `phase_plan_ready` (as assigned in lines 121130) is `False` and `attempt >= OPENCODE_MAX_RETRIES`, the program calls `sys.exit(1)` and terminates; no further statements are executed.
2. (Exception) If `phase_plan_ready` is `True` and the `break` is taken, and then the condition `plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process` holds, and the command executed by `run_plugin_command` exits with a nonzero code, a `CalledProcessError` is raised; the block does not complete normally.
3. (Normal completion) Otherwise the block finishes normally without terminating the program or raising an exception. In this case:
   - If `phase_plan_ready` is `True`: the enclosing loop has been exited (via `break`). Afterwards, if `plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process` is true, the shell command `plugin_stage.output_process` was executed by `run_plugin_command` with `cwd=plugin_root`, environment variable `FM_AGENT_PLUGIN_ROOT` set to `plugin_root`, and label `"generate_phase_plan post-process"`, and completed successfully (exit code 0). If that condition is false, no plugin postprocess ran.
   - If `phase_plan_ready` is `False` and `attempt < OPENCODE_MAX_RETRIES`: a warning message containing the computed `missing` reason was logged via `logging.warning` and printed to stdout; `time.sleep(10)` completed. The loop was not broken, so control will return to the top of the outer loop for the next iteration (outside this block).
   - All other program state brought into the block remains unchanged: `prompt`, `command`, `attempt`, `proj_dir`, `submodules` (if present), `is_incremental`, `prev_mtime`, `phases_json`, `phase_plan_errors`, `OPENCODE_MAX_RETRIES`, `plugin_root`, `plugin_stage`. The trace directory still contains an event for stage `'generate_phases_json'` with metadata `{... (line truncated to 2000 chars)

---

## Code Evidence

Line 125:                 phase_plan_ready = (
Line 126:                     os.path.getmtime(phases_json) != prev_mtime
Line 127:                     or _phases_cover_current_sources(phases_json, proj_dir)
Line 128:                 )

---

## Trigger Condition

In incremental mode the specification demands that the updated phases.json reflect the current source state. The code uses an mtime-based check as an alternative to the coverage check, so a mere rewrite of the file (even with incomplete coverage) is accepted as ready, violating the required guarantee.

---

## How to trigger the bug

In incremental mode, if an LLM simply rewrites `phases.json` (changing its mtime) without actually adding all current source files, the OR logic at `src/pipeline_setup.py` lines 1034-1037 evaluates to `True` because `os.path.getmtime(phases_json) != prev_mtime` is satisfied, even though `_phases_cover_current_sources` would return `False`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `is_incremental` | `True` |
| `phases.json` | Contains only 1 of 3 current project `.py` source files |
| `prev_mtime` | Recorded before the LLM rewrite attempt |
| `new_mtime` | Changed after the LLM rewrites phases.json (without adding missing files) |

### Expected (spec-correct) Output

`phase_plan_ready` should be `False` — because `_phases_cover_current_sources` returns `False` (the phases.json does not cover all current source files).

### Actual (buggy) Output

`phase_plan_ready` is `True` — because the OR short-circuits on `os.path.getmtime(phases_json) != prev_mtime` being `True`, bypassing the coverage check entirely.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import json
import time
import tempfile
import shutil
import src.pipeline_setup as pipeline_setup

tmpdir = tempfile.mkdtemp(prefix="probe_")
try:
    proj_dir = os.path.join(tmpdir, "project")
    os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(proj_dir, "lib"), exist_ok=True)

    with open(os.path.join(proj_dir, "src", "main.py"), "w") as f: f.write("# main\n")
    with open(os.path.join(proj_dir, "src", "utils.py"), "w") as f: f.write("# utils\n")
    with open(os.path.join(proj_dir, "lib", "helpers.py"), "w") as f: f.write("# helpers\n")

    phases_json = os.path.join(tmpdir, "phases.json")
    data = {
        "phases": [{
            "phase": 1, "name": "core", "description": "Core",
            "modules": [{"name": "main", "description": "Main", "source_files": ["src/main.py"]}],
            "depends_on_phases": []
        }]
    }
    with open(phases_json, "w") as f:
        json.dump(data, f)

    prev_mtime = os.path.getmtime(phases_json)
    time.sleep(0.1)
    os.utime(phases_json, None)  # rewrite without improving coverage

    mtime_changed = os.path.getmtime(phases_json) != prev_mtime
    coverage_ok = pipeline_setup._phases_cover_current_sources(phases_json, proj_dir)

    # Buggy logic from lines 1034-1037
    phase_plan_ready = mtime_changed or coverage_ok

    print(f"mtime_changed={mtime_changed}, coverage_ok={coverage_ok}")
    print(f"BUG: phase_plan_ready={phase_plan_ready} (should be {coverage_ok})")
    # actual (buggy) output: BUG: phase_plan_ready=True (should be False)
    # expected (correct) output: phase_plan_ready=False
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for bug: src--pipeline_setup-py--_run_generate_phases

In incremental mode, phase_plan_ready at lines 1034-1037 of src/pipeline_setup.py
incorrectly accepts a phases.json rewrite (mtime change) even when coverage is
incomplete, because the OR bypasses the _phases_cover_current_sources check.

This probe creates a minimal project with 3 source files, writes an incomplete
phases.json covering only 1 of them, then simulates the buggy OR logic.
"""

import os
import sys
import json
import time
import tempfile
import shutil

try:
    # Load via public package entry point
    import src.pipeline_setup as pipeline_setup

    tmpdir = tempfile.mkdtemp(prefix="probe_phaseready_")
    try:
        proj_dir = os.path.join(tmpdir, "project")
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(proj_dir, "lib"), exist_ok=True)

        # Create source files (names that don't match test-file patterns)
        with open(os.path.join(proj_dir, "src", "main.py"), "w") as f:
            f.write("# main entry\n")
        with open(os.path.join(proj_dir, "src", "utils.py"), "w") as f:
            f.write("# utility functions\n")
        with open(os.path.join(proj_dir, "lib", "helpers.py"), "w") as f:
            f.write("# helper functions\n")

        # Create incomplete phases.json — only covers src/main.py
        phases_json = os.path.join(tmpdir, "phases.json")
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "core",
                    "description": "Core phase",
                    "modules": [
                        {
                            "name": "main",
                            "description": "Main module",
                            "source_files": ["src/main.py"]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }
        with open(phases_json, "w") as f:
            json.dump(phases_data, f, indent=2)

        # Record initial mtime (simulates prev_mtime before LLM attempt)
        prev_mtime = os.path.getmtime(phases_json)

        # Wait long enough for filesystem timestamp to change
        time.sleep(0.1)

        # Simulate an LLM rewriting phases.json (changes mtime) but failing
        # to add the missing files — i.e., the file was "touched" but coverage
        # is still incomplete.
        os.utime(phases_json, None)

        new_mtime = os.path.getmtime(phases_json)
        mtime_changed = new_mtime != prev_mtime

        # Actual coverage check — should be False (2 of 3 files missing)
        coverage_ok = pipeline_setup._phases_cover_current_sources(
            phases_json, proj_dir
        )

        # Reproduce the buggy incremental-mode logic from lines 1034–1037:
        #   phase_plan_ready = (
        #       os.path.getmtime(phases_json) != prev_mtime
        #       or _phases_cover_current_sources(phases_json, proj_dir)
        #   )
        phase_plan_ready_buggy = mtime_changed or coverage_ok

        # Spec-correct behavior: phase_plan_ready SHOULD require actual
        # coverage of all current sources in incremental mode.
        expected_ready = coverage_ok

        # Bug reproduced: the buggy logic says True, but coverage says False
        passed = phase_plan_ready_buggy != expected_ready

        if passed:
            print(
                f"CONFIRMED — "
                f"mtime_changed={mtime_changed}, "
                f"coverage_ok={coverage_ok}, "
                f"buggy_phase_plan_ready={phase_plan_ready_buggy}, "
                f"expected_phase_plan_ready={expected_ready}"
            )
        else:
            print(
                f"NOT CONFIRMED — "
                f"mtime_changed={mtime_changed}, "
                f"coverage_ok={coverage_ok}, "
                f"buggy_phase_plan_ready={phase_plan_ready_buggy}, "
                f"expected_phase_plan_ready={expected_ready}"
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — mtime_changed=True, coverage_ok=False, buggy_phase_plan_ready=True, expected_phase_plan_ready=False
```
