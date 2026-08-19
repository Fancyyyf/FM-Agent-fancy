# Bug Report: _run_generate_domain_context

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the function returns normally (without exiting the process): either plugin_stage.type is 'pass' or 'replace' (the plugin assumes full responsibility for domain context output), or engine_overview.txt exists at work_dir/spec_prompts/domain_context/ describing the overall system architecture and cross-cutting invariants AND for every phase number defined in phases.json, a corresponding phase_NN_types.txt file exists at work_dir/spec_prompts/domain_context/ describing the types, data structures, and invariants for the source files assigned to that phase. If after OPENCODE_MAX_RETRIES attempts any required domain context output file is missing from its expected location, the process exits with code 1 and emits a diagnostic message that enumerates the expected outputs.

---

### Actual Behavior

After the code block finishes, the following possible outcomes exist:

1. **Normal completion (domain context obtained):** If `_resume_skip` was `True` at entry, the loop is immediately broken out of and no LLM attempts are made. Otherwise (`_resume_skip == False`), the for loop executes up to `OPENCODE_MAX_RETRIES` attempts, and after a successful attempt (i.e., when `_domain_context_complete(work_dir)` becomes true) the loop breaks. In both cases, after the loop the optional plugin postprocessing step runs (if `plugin_stage` is not `None`, `plugin_stage.type == 'modify'` and `plugin_stage.output_process` is truthy) by calling `run_plugin_command(plugin_stage.output_process, plugin_root, proj_dir, label='generate_domain_context post-process')`. If this command raises a `CalledProcessError`, the exception propagates uncaught. Otherwise the code block ends normally. Under this normal termination the following hold:
   - `_domain_context_complete(work_dir)` is `True` (the required domain context output files, including `fm_agent/spec_prompts/domain_context/engine_overview.txt`, exist).
   - The workflow file `workflow_generate_domain_context.md` in `work_dir` still exists, unchanged except possibly by the plugin postprocess.
   - The plugin postprocess command, if configured, completed without error.
   - No unhandled exception occurred.

2. **Failure after all retries:** If `_resume_skip` is `False` and after `OPENCODE_MAX_RETRIES` attempts the condition `_domain_context_complete(work_dir)` has never become true, the function prints an error message and calls `sys.exit(1)`, terminating the process. No further code after the loop is executed, and the domain context remains incomplete.

3. **Exception during postprocessing:** If the plugin postprocess command raises `CalledProcessError`, the exception propagates out of the code block and the domain context may be complete but the postprocess failed.

Formally, for the normal completion case, the domain context output is complete and the workflow file is intact. The failure mode (2) is the only one relevant to the diagnostic message mismatch: the error message does not enumerate all required outputs.

---

## Code Evidence

Line 93:             print(
Line 94:                 f"[Pipeline] ERROR: Stage 2 failed after {OPENCODE_MAX_RETRIES} attempts. "
Line 95:                 f"Domain context outputs missing. "
Line 96:                 f"Check {os.path.basename(proj_dir)}/fm_agent/trace/ for details."
Line 97:             )

---

## Trigger Condition

The specification requires that when the process exits after exhausting retries, the diagnostic message must enumerate the expected output files. The code's error message (lines 93-97) only states outputs are missing and refers to the trace directory, without listing the concrete required files (e.g., engine_overview.txt and phase_NN_types.txt for each phase in phases.json).

---

## How to trigger the bug

When `_run_generate_domain_context` exhausts all `OPENCODE_MAX_RETRIES` attempts without producing complete domain context output, the function prints a failure message and exits. The printed message says "Domain context outputs missing" but does not enumerate the specific required files (engine_overview.txt, phase_NN_types.txt), violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory containing `fm_agent/` with a valid `phases.json` but no domain context files |
| `work_dir` | `${proj_dir}/fm_agent` |
| `script_dir` | Arbitrary (patched in test) |
| `resume` | `False` |
| `plugin_stage` | `None` |
| `OPENCODE_MAX_RETRIES` (patched) | `1` |

### Expected (spec-correct) Output

The error message should enumerate the expected output files, e.g.:
`Domain context outputs missing. Expected: engine_overview.txt, phase_01_types.txt. Check fake_project/fm_agent/trace/ for details.`

### Actual (buggy) Output

`[Pipeline] ERROR: Stage 2 failed after 1 attempts. Domain context outputs missing. Check fake_project/fm_agent/trace/ for details.`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile, io
from unittest.mock import patch

import src.pipeline_setup as ps

with tempfile.TemporaryDirectory() as tmpdir:
    proj_dir = os.path.join(tmpdir, "fake_project")
    work_dir = os.path.join(proj_dir, "fm_agent")
    os.makedirs(work_dir, exist_ok=True)
    phases = {"phases": [{"phase": 1, "description": "Test Phase"}]}
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases, f)

    captured = io.StringIO()
    with patch("src.pipeline_setup.OPENCODE_MAX_RETRIES", 1), \
         patch("src.pipeline_setup._prepare_workflow_file", return_value=None), \
         patch("src.pipeline_setup.run_opencode_traced", return_value=None):
        old_stdout = sys.stdout
        try:
            sys.stdout = captured
            try:
                ps._run_generate_domain_context(proj_dir, work_dir, "/nonexistent", resume=False)
            except SystemExit:
                pass
        finally:
            sys.stdout = old_stdout
    print(repr(captured.getvalue()))
# actual (buggy) output: '[Pipeline] ERROR: Stage 2 failed after 1 attempts. Domain context outputs missing. Check fake_project/fm_agent/trace/ for details.\n'
# expected (correct) output: message should include 'engine_overview.txt' and 'phase_01_types.txt'
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import io
from unittest.mock import patch

# Ensure the repo root is on sys.path so that `import src` works.
# The probe lives at fm_agent/bug_validation/probe_<id>.py, so repo root is
# three levels up from the script directory.
_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def test_bug():
    import src.pipeline_setup as ps

    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = os.path.join(tmpdir, "fake_project")
        work_dir = os.path.join(proj_dir, "fm_agent")
        os.makedirs(work_dir, exist_ok=True)

        # Create a valid phases.json so _domain_context_complete won't fail early
        # on a missing/broken JSON, but don't create any domain context files so
        # it returns False after checking engine_overview.txt and phase_NN_types.txt
        phases = {"phases": [{"phase": 1, "description": "Test Phase"}]}
        with open(os.path.join(work_dir, "phases.json"), "w") as f:
            json.dump(phases, f)

        captured = io.StringIO()

        # OPENCODE_MAX_RETRIES is imported into pipeline_setup via
        #   from config import OPENCODE_MAX_RETRIES
        # Patch the module-level binding so range(1, OPENCODE_MAX_RETRIES + 1)
        # produces exactly one iteration.
        #
        # run_opencode_traced is imported via
        #   from .opencode_trace import run_opencode_traced
        # Patch its module-level binding so the LLM call is a no-op.
        #
        # _prepare_workflow_file is defined in the same module; patching it
        # avoids touching the real filesystem beyond our tempdir.
        with patch("src.pipeline_setup.OPENCODE_MAX_RETRIES", 1), \
             patch("src.pipeline_setup._prepare_workflow_file", return_value=None), \
             patch("src.pipeline_setup.run_opencode_traced", return_value=None):

            old_stdout = sys.stdout
            try:
                sys.stdout = captured
                try:
                    ps._run_generate_domain_context(
                        proj_dir, work_dir, "/nonexistent",
                        resume=False,
                    )
                except SystemExit as e:
                    # sys.exit(1) is expected when retries are exhausted
                    if e.code != 1:
                        raise
            finally:
                sys.stdout = old_stdout

        output = captured.getvalue()

        # The specification requires that the diagnostic message after exhausting
        # retries "enumerates the expected outputs."
        #
        # Expected: message should mention concrete file names such as
        # "engine_overview.txt" and "phase_NN_types.txt" for each phase.
        #
        # The actual code (lines 1224-1229) only says:
        #   "Domain context outputs missing. Check <proj>/fm_agent/trace/ for details."
        # It does NOT enumerate any output file names.
        expected_outputs_mentioned = any(
            keyword in output
            for keyword in ("engine_overview.txt", "phase_", "phase_01_types")
        )

        if expected_outputs_mentioned:
            print("NOT CONFIRMED — error message enumerates expected outputs")
        else:
            print(
                "CONFIRMED — actual: "
                + repr(output)
                + " | expected: diagnostic message should enumerate expected output "
                + "filenames (e.g. engine_overview.txt, phase_NN_types.txt)"
            )


if __name__ == "__main__":
    try:
        test_bug()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '[Pipeline] ERROR: Stage 2 failed after 1 attempts. Domain context outputs missing. Check fake_project/fm_agent/trace/ for details.\n' | expected: diagnostic message should enumerate expected output filenames (e.g. engine_overview.txt, phase_NN_types.txt)
```
