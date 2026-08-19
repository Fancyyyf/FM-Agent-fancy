# Bug Report: _setup_outputs_complete

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_setup_outputs_complete.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True if and only if all of the following exist at their expected paths under work_dir: (1) phases.json, (2) spec_prompts/domain_context/engine_overview.txt, and (3) for every phase number P declared in the phases.json file, a file spec_prompts/domain_context/phase_P_types.txt

---

### Actual Behavior

The function returns True if and only if both the phase plan and domain context are complete: the file 'phases.json' exists under 'work_dir' and contains a valid phases plan, the file 'engine_overview.txt' exists under 'work_dir', and for every phase number P defined in that 'phases.json', the file 'phase_P_types.txt' exists under 'work_dir'. Returns False otherwise.

---

## Code Evidence

Line 3: return _phase_plan_complete(work_dir) and _domain_context_complete(work_dir)

---

## Trigger Condition

The specification requires engine_overview.txt and phase_P_types.txt to be placed under the spec_prompts/domain_context/ subdirectory. The actual code checks for these files directly under work_dir (as per Condition A). Thus, when the required files exist directly under work_dir but not in the subdirectory, the code returns True, violating the specification which expects False.

---

## How to trigger the bug

The bug could not be reproduced. The LLM analysis that produced the "actual behavior" description mischaracterized the code. The `_domain_context_complete` function (called by `_setup_outputs_complete` at line 719 of `src/pipeline_setup.py`) actually constructs `domain_dir` as `os.path.join(work_dir, "spec_prompts", "domain_context")` at line 696 and checks for `engine_overview.txt` and `phase_*_types.txt` files under that subdirectory — exactly matching the specification.

When files are placed directly under `work_dir` (e.g., `work_dir/engine_overview.txt`) without the `spec_prompts/domain_context/` subdirectory, the code correctly returns `False`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A temporary directory containing `phases.json` (valid), `engine_overview.txt` (directly under work_dir), and `phase_01_types.txt` (directly under work_dir). No `spec_prompts/domain_context/` subdirectory exists. |

### Expected (spec-correct) Output

`False` — files at wrong location (not under `spec_prompts/domain_context/`) should not satisfy the completeness check.

### Actual (buggy) Output

`False` — The actual output matches the expected output. The code correctly rejects the files placed at the wrong location.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile
import sys
sys.path.insert(0, ".")
from src.pipeline_setup import _setup_outputs_complete

tmpdir = tempfile.mkdtemp()
with open(os.path.join(tmpdir, "phases.json"), "w") as f:
    json.dump({"phases": [{"phase": 1, "name": "Test", "modules": [{"name": "m", "source_files": ["f.py"], "description": "d"}]}]}, f)
open(os.path.join(tmpdir, "engine_overview.txt"), "w").close()
open(os.path.join(tmpdir, "phase_01_types.txt"), "w").close()

result = _setup_outputs_complete(tmpdir)
# actual (buggy) output: False
# expected (correct) output: False
print(f"result = {result!r}")
```

---

## Probe Script

```python
"""Probe for bug src--pipeline_setup-py--_setup_outputs_complete.

Bug claim: _setup_outputs_complete checks for engine_overview.txt and
phase_P_types.txt directly under work_dir, when the spec requires them under
spec_prompts/domain_context/.

Test: Create files at work_dir/ directly (wrong location, NOT under
spec_prompts/domain_context/) with a valid phases.json. If the code accepts
them, the bug is confirmed. If it correctly rejects them, NOT CONFIRMED.
"""

import sys
import os
import json
import shutil
import tempfile
import traceback


def main():
    # Ensure the project root is on sys.path so that 'src' is importable.
    # The probe lives at fm_agent/bug_validation/probe_*.py under repo root.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    tmpdir = tempfile.mkdtemp(prefix="bug_probe_sup_outputs_")
    try:
        # Load the function via the public package entry point
        from src.pipeline_setup import _setup_outputs_complete

        work_dir = tmpdir

        # Build a valid phases.json with one phase
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Test Phase",
                    "modules": [
                        {
                            "name": "test_module",
                            "source_files": ["test.py"],
                            "description": "test module",
                        }
                    ],
                    "depends_on_phases": [],
                }
            ]
        }
        with open(os.path.join(work_dir, "phases.json"), "w") as f:
            json.dump(phases_data, f)

        # Place files directly under work_dir (THE WRONG LOCATION per spec).
        # Spec requires: work_dir/spec_prompts/domain_context/engine_overview.txt
        #                work_dir/spec_prompts/domain_context/phase_01_types.txt
        # Bug claim says code checks directly under work_dir, so these files
        # would cause a True return when the spec expects False.
        with open(os.path.join(work_dir, "engine_overview.txt"), "w") as f:
            f.write("test engine overview\n")
        with open(os.path.join(work_dir, "phase_01_types.txt"), "w") as f:
            f.write("test phase types\n")

        # DELIBERATELY do NOT create spec_prompts/domain_context/ subdirectory.

        # _phase_plan_complete(work_dir) will return True (valid phases.json exists).
        # _domain_context_complete(work_dir) checks:
        #   work_dir/spec_prompts/domain_context/engine_overview.txt  -> does NOT exist
        #   work_dir/spec_prompts/domain_context/phase_01_types.txt   -> does NOT exist
        # So if code is correct, it returns False.
        # If bug exists (code checks directly under work_dir), it returns True.

        result = _setup_outputs_complete(work_dir)

        # Spec says: files at spec_prompts/domain_context/ -> True; else False
        expected = False
        actual = result

        if actual == expected:
            print(
                f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r} "
                f"(code correctly rejected files at wrong path)"
            )
        else:
            print(
                f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
                f"(bug reproduced: code accepted files at wrong path)"
            )

    except Exception as exc:
        print(f"ERROR: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — actual: False | expected: False (code correctly rejected files at wrong path)
```
