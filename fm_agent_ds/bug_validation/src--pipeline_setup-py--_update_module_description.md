# Bug Report: _update_module_description

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_update_module_description.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If modified_modules is empty, the function returns immediately with no side effects. If no phases.json file exists at the expected path under work_dir, the function logs an informational message and returns with no side effects. If no module identified in modified_modules still owns any source files in the current phases.json, the function logs an informational message and returns with no side effects. Otherwise: the description field of every module identified in modified_modules that still owns source files in phases.json is rewritten to accurately describe the module's current set of source files, written to the phases.json file at the expected path under work_dir. The rewriting is performed by an LLM agent invoked with up to OPENCODE_MAX_RETRIES attempts. If all retry attempts fail, the function logs a warning and returns without modifying phases.json  stale module descriptions are non-fatal to the pipeline.

---

### Actual Behavior

The function always returns None and never raises an unhandled exception. If `modified_modules` is empty, or the file `phases.json` does not exist at `os.path.join(work_dir, "phases.json")`, or `_build_module_description_prompt` returns None, no side effects occur: the file system remains exactly as it was before the call. Otherwise (`modified_modules` nonempty, `phases.json` exists, and at least one module still owns source files), the function loops up to OPENCODE_MAX_RETRIES, calling `run_opencode_traced` for each attempt. If any call succeeds, then after the function returns, the file `os.path.join(work_dir, "fm_agent", "phases.json")` exists and contains the LLM agent's rewritten descriptions for the modules that had source files, while the original `work_dir/phases.json` is unchanged; no other files are guaranteed to be modified. If all attempts fail, the function logs a warning and returns; the state of `work_dir/fm_agent/phases.json` is unspecified (it may be absent, unchanged, or corrupted). The arguments `proj_dir`, `work_dir`, and `modified_modules` are not modified.

---

## Code Evidence

Line 41: output_files=["fm_agent/phases.json"]

---

## Trigger Condition

The specification requires that the updated module descriptions be written to the phases.json file at the expected path under work_dir (the same file checked for existence on line 15-16). However, the code configures the agent to write its output to a different file, work_dir/fm_agent/phases.json, and never modifies the original work_dir/phases.json. As a result, after the function returns, the original phases.json remains unchanged, violating the requirement.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | (temporary directory path) |
| `work_dir` | (temporary directory containing `phases.json` with one module owning `src/test.py`) |
| `modified_modules` | `[{"phase": 1, "module": "test_module"}]` |

### Expected (spec-correct) Output

`work_dir/phases.json` should contain updated module descriptions after the function returns successfully. The `output_files` parameter to `run_opencode_traced` should be `["phases.json"]` (resolving to `work_dir/phases.json`).

### Actual (buggy) Output

`work_dir/phases.json` remains completely unchanged. The function passes `output_files=["fm_agent/phases.json"]` to `run_opencode_traced`, which resolves to `work_dir/fm_agent/phases.json` — a different file than the one the spec requires to be updated.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from unittest.mock import patch

tmpdir = tempfile.mkdtemp()
work_dir = os.path.join(tmpdir, "work")
os.makedirs(work_dir)
phases_content = {"phases": [{"phase": 1, "name": "Test", "modules": [
    {"name": "test_module", "description": "orig", "source_files": ["src/test.py"]}
]}]}
with open(os.path.join(work_dir, "phases.json"), "w") as f:
    json.dump(phases_content, f)

with patch("src.pipeline_setup.run_opencode_traced") as mock_run, \
     patch("src.pipeline_setup.build_llm_cli_command", return_value=["echo"]):
    from src.pipeline_setup import _update_module_description
    _update_module_description(tmpdir, work_dir, [{"phase": 1, "module": "test_module"}])

# output_files is ["fm_agent/phases.json"], NOT ["phases.json"]
print(mock_run.call_args.kwargs["output_files"])
# actual (buggy) output: ['fm_agent/phases.json']
# expected (correct) output: ['phases.json']
```

---

## Probe Script

```python
"""Probe script for bug src--pipeline_setup-py--_update_module_description.

Bug: _update_module_description passes output_files=["fm_agent/phases.json"] to
run_opencode_traced, causing the LLM agent to write to work_dir/fm_agent/phases.json
instead of the spec-required work_dir/phases.json. After the function returns
successfully, work_dir/phases.json (the file it checks existence for on line 573)
remains unchanged.
"""

import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch

# Ensure the repo root is on sys.path so that 'src' can be imported.
# When run as `python3 fm_agent/bug_validation/probe_*.py`, Python adds
# fm_agent/bug_validation/ to sys.path[0], not the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    tmpdir = tempfile.mkdtemp(prefix="probe_update_mod_desc_")
    work_dir = os.path.join(tmpdir, "work")
    os.makedirs(work_dir)

    # Build a minimal phases.json with a module that owns a source file
    phases_content = {
        "phases": [
            {
                "phase": 1,
                "name": "Test Phase",
                "description": "Phase description.",
                "modules": [
                    {
                        "name": "test_module",
                        "description": "Original module description.",
                        "source_files": ["src/test.py"],
                    }
                ],
                "depends_on_phases": [],
            }
        ]
    }
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(phases_content, f)

    # Mock run_opencode_traced and build_llm_cli_command so we can call the
    # function without invoking OpenCode (FM-Agent self-validation guard).
    with (
        patch("src.pipeline_setup.run_opencode_traced") as mock_run,
        patch("src.pipeline_setup.build_llm_cli_command") as mock_build,
    ):
        # build_llm_cli_command returns a dummy command list
        mock_build.return_value = ["echo", "mocked"]

        from src.pipeline_setup import _update_module_description

        modified_modules = [{"phase": 1, "module": "test_module"}]
        proj_dir = tmpdir  # not used by the function directly, only passed through

        _update_module_description(proj_dir, work_dir, modified_modules)

        # --- Verification ---
        # 1. run_opencode_traced was called exactly once
        mock_run.assert_called_once()

        # 2. The output_files parameter was "fm_agent/phases.json" — proving
        #    the agent is told to write to work_dir/fm_agent/phases.json, NOT
        #    work_dir/phases.json as the spec requires.
        call_kwargs = mock_run.call_args.kwargs
        output_files = call_kwargs.get("output_files")

        bug_reproduced = output_files == ["fm_agent/phases.json"]

        # 3. The file work_dir/phases.json was NOT modified by this call
        #    (it still has the original content). The spec says it should be
        #    rewritten with updated descriptions.
        with open(phases_path, "r") as f:
            after = json.load(f)
        file_unchanged = after == phases_content

        if bug_reproduced and file_unchanged:
            print(
                "CONFIRMED — output_files=[\"fm_agent/phases.json\"] tells the LLM agent "
                "to write to work_dir/fm_agent/phases.json instead of work_dir/phases.json. "
                "After the function returned, work_dir/phases.json was NOT modified "
                "(unchanged=True), violating the spec requirement that updated "
                "descriptions be written to the phases.json at the expected path "
                "under work_dir."
            )
        elif bug_reproduced:
            print(
                "CONFIRMED — output_files=[\"fm_agent/phases.json\"] tells the LLM agent "
                "to write to work_dir/fm_agent/phases.json instead of work_dir/phases.json, "
                "violating the spec."
            )
        else:
            print(
                f"NOT CONFIRMED — expected output_files=[\"fm_agent/phases.json\"], "
                f"got output_files={output_files!r}"
            )

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    # Clean up temp directory
    if "tmpdir" in dir() and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — output_files=["fm_agent/phases.json"] tells the LLM agent to write to work_dir/fm_agent/phases.json instead of work_dir/phases.json. After the function returned, work_dir/phases.json was NOT modified (unchanged=True), violating the spec requirement that updated descriptions be written to the phases.json at the expected path under work_dir.
```
