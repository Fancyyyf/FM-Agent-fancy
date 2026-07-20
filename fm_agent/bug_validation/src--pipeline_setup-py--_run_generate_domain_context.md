# Bug Report: _run_generate_domain_context

**Source file:** `fm_agent/extracted_functions/src/pipeline_setup-py/_run_generate_domain_context.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- On normal return: the directory spec_prompts/domain_context/ within work_dir contains engine_overview.txt and exactly one file matching the pattern phase_NN_types.txt for each phase defined in phases.json
  - When resume is truthy and the domain context files under spec_prompts/domain_context/ already satisfy the pipeline's completeness criteria, the function returns without producing or modifying any files
  - If complete domain context is not produced after a configurable maximum number of retry attempts, the function prints a diagnostic message to stdout identifying the failed stage and the trace directory, then calls sys.exit(1)
  - When a non-final attempt fails to produce complete domain context, the function does not call sys.exit(1)  it waits a fixed interval before retrying
  - Staged domain knowledge files under spec_prompts/domain_context/user_knowledge/ are supplied as inputs to the generation process

---

### Actual Behavior

Natural Language Post-condition:
After execution, if the function returns normally (no exception and no call to sys.exit), then the workflow file 'workflow_generate_domain_context.md' exists under fm_agent/ in the project directory, and the domain context completeness condition holds (i.e., _domain_context_complete(work_dir) returns True). If the function raises an unhandled exception (e.g., from file operations), the state is partially updated (with the workflow file possibly created) and no guarantees about completeness are made. If the function calls sys.exit(1) after exhausting all retries, the process terminates with exit code 1 and the domain context remains incomplete.

Formal Logic:
Let proj_dir, work_dir, script_dir be given. After the function call, if control returns to the caller (i.e., no exception and no SystemExit), then:

  (exists md_path = proj_dir / "fm_agent" / "workflow_generate_domain_context.md" such that is_file(md_path))
  AND
  _domain_context_complete(work_dir) = True

If a SystemExit exception occurs (from sys.exit(1)), the interpreter is terminated and no post-condition is applicable. For any other unhandled exception, the post-condition is undefined (side effects prior to the exception may persist).

---

## Code Evidence

Line 8: _prepare_workflow_file(proj_dir, work_dir, script_dir, "workflow_generate_domain_context.md")

---

## Trigger Condition

The specification states: 'When resume is truthy and the domain context files under spec_prompts/domain_context/ already satisfy the pipeline's completeness criteria, the function returns without producing or modifying any files.' The code unconditionally calls _prepare_workflow_file on Line 8 before the early-exit check, causing a file to be copied (produced/modified) even when the resume-skip condition is met. This concrete input triggers that exact violation.

---

## How to trigger the bug

The function `_run_generate_domain_context` in `src/pipeline_setup.py` computes `_resume_skip = resume and _domain_context_complete(work_dir)` on line 1003, prints a resume message if true, but then falls through to call `_prepare_workflow_file` on line 1007 unconditionally — it is outside the `if _resume_skip` block. When `resume=True` and domain context is already complete, the spec requires returning without producing or modifying any files, yet `workflow_generate_domain_context.md` is always copied into the work directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | temp directory (not used for file creation) |
| `work_dir` | temp directory with complete domain context (phases.json + engine_overview.txt + phase_01_types.txt) |
| `script_dir` | repo root (contains `md/workflow_generate_domain_context.md`) |
| `resume` | `True` |

### Expected (spec-correct) Output

No files created or modified in `work_dir`. The function should return immediately.

### Actual (buggy) Output

`workflow_generate_domain_context.md` was created in `work_dir` (3002 bytes). The function copied it from `script_dir/md/workflow_generate_domain_context.md` despite the resume-skip condition being met.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile, shutil
sys.path.insert(0, os.getcwd())

from src.pipeline_setup import _run_generate_domain_context

work_dir = tempfile.mkdtemp()
with open(os.path.join(work_dir, "phases.json"), "w") as f:
    json.dump({"phases": [{"phase": 1}]}, f)
domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
os.makedirs(domain_dir)
with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
    f.write("ok\n")
with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
    f.write("ok\n")

# Spec says no files should be produced — but this creates workflow_generate_domain_context.md
_run_generate_domain_context(tempfile.mkdtemp(), work_dir, os.getcwd(), resume=True)

print("File created:", os.path.exists(os.path.join(work_dir, "workflow_generate_domain_context.md")))
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```py
"""Probe script for bug src--pipeline_setup-py--_run_generate_domain_context.

Bug: _prepare_workflow_file is called unconditionally before the resume-skip check,
so when resume=True and domain context is already complete, the function still
copies workflow_generate_domain_context.md — violating the spec which says it
should return "without producing or modifying any files".
"""
import sys
import os
import json
import tempfile
import shutil

# Determine repo root and add to Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # fm_agent/bug_validation/ -> fm_agent/ -> repo root
sys.path.insert(0, REPO_ROOT)

from src.pipeline_setup import _run_generate_domain_context


def main():
    proj_dir = tempfile.mkdtemp(prefix="dummy_proj_")
    script_dir = REPO_ROOT
    work_dir = tempfile.mkdtemp(prefix="bug_probe_")

    try:
        # ── Set up work_dir so _domain_context_complete() returns True ──
        phases_json = os.path.join(work_dir, "phases.json")
        with open(phases_json, "w") as f:
            json.dump({"phases": [{"phase": 1, "name": "Test Phase"}]}, f)

        domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
        os.makedirs(domain_dir, exist_ok=True)

        with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
            f.write("Test engine overview.\n")

        with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
            f.write("Test type definitions.\n")

        # ── Pre-condition: workflow file must NOT exist yet ──
        workflow_file = os.path.join(work_dir, "workflow_generate_domain_context.md")
        file_existed_before = os.path.exists(workflow_file)

        # ── Call the function with resume=True ──
        # Spec says: "When resume is truthy and the domain context files ...
        # already satisfy the pipeline's completeness criteria, the function
        # returns without producing or modifying any files."
        try:
            _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=True)
        except SystemExit:
            pass

        # ── Check result ──
        file_created = os.path.exists(workflow_file)

        if file_created and not file_existed_before:
            actual_size = os.path.getsize(workflow_file)
            print(
                f"CONFIRMED — actual: workflow_generate_domain_context.md was created "
                f"({actual_size} bytes) at {workflow_file} | "
                f"expected per spec: no files should be produced or modified"
            )
        elif file_created:
            actual_size = os.path.getsize(workflow_file)
            print(
                f"CONFIRMED — actual: workflow_generate_domain_context.md was modified "
                f"({actual_size} bytes) | "
                f"expected per spec: no files should be produced or modified"
            )
        else:
            print(
                "NOT CONFIRMED — workflow file was not created; "
                "actual matched expected (no files produced)"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(proj_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
[Pipeline] Stage 2/6: RESUME — domain context files found, skipping domain context generation.
CONFIRMED — actual: workflow_generate_domain_context.md was created (3002 bytes) at /tmp/bug_probe_1xt3a6oc/workflow_generate_domain_context.md | expected per spec: no files should be produced or modified
```
