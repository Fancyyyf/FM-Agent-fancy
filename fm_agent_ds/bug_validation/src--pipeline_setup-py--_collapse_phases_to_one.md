# Bug Report: _collapse_phases_to_one

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_collapse_phases_to_one.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If phases.json contained at least one phase, the file under work_dir is rewritten such that: (1) the 'phases' array contains exactly one phase element; (2) the single phase's 'modules' array is the concatenation, in ascending 'phase' order, of every 'modules' array from all original phases, with the relative ordering of modules within each original phase's 'modules' array preserved; (3) the single phase's 'description' is a string formed by joining the stripped, non-empty descriptions of all original phases in ascending 'phase' order with a blank-line separator; (4) the single phase's 'depends_on_phases' is an empty list. Additionally, if one or more 'phase_*_types.txt' files exist under '<work_dir>/spec_prompts/domain_context/', their stripped contents are concatenated in ascending phase order (separated by blank lines) and written to 'phase_01_types.txt' in the same directory, then all other 'phase_*_types.txt' files in that directory are deleted. If phases.json contained zero phases, no file modifications occur.

---

### Actual Behavior

If the 'phases' list is empty, the file system remains unchanged and the function returns immediately. Otherwise, after normal execution (no exceptions):

1. The file at phases_path (work_dir/phases.json) is overwritten with a JSON object whose 'phases' key holds a single-element list containing a merged phase object M. M has the same keys as the first phase in the original sorted list (including its original 'phase' number, which may not necessarily be 1), with the following modifications:
   - 'name' is set to "Unified Analysis Phase".
   - 'description' is the concatenation of all nonempty, stripped 'description' strings from every original phase, in sorted order, separated by "\n\n". If none are nonempty, this field is present but empty.
   - 'modules' is a list containing every module dictionary from every original phase, preserving the order of phases and the order of modules within each phase.
   - 'depends_on_phases' is set to an empty list [].

2. In the directory work_dir/spec_prompts/domain_context:
   a. Let T be the set of paths phase_{:02d}_types.txt for each original phase (using its 'phase' number, zero-padded to two digits).
   b. If at least one such file existed, a single file phase_01_types.txt is created (or overwritten) containing the stripped contents of all existing files in T, concatenated in order with "\n\n" separators and a trailing newline. All other files matching the glob pattern "phase_*_types.txt" in that directory (including any that were not in T) are deleted, except the newly written phase_01_types.txt. After this step, the only file matching that pattern is phase_01_types.txt with the merged content.
   c. If no file from T existed, no new file is created and no files are deleted; the directory remains as is.

All operations assume existing files and directories required by the precondition are readable/writable. If an I/O error occurs (e.g., inability to write phases.json or create/move domain_context files), a Python exception propagates from the function.

**Key difference**: The spec requires the merged description to contain only the stripped, non-empty descriptions joined by blank lines. The actual behavior inserts a `"Phase {N} ({Name}): "` prefix before each description.

---

## Code Evidence

Line 10: f\"Phase {phase['phase']} ({phase['name']}): {phase_description}\"

---

## Trigger Condition

The specification requires the merged description to be just the stripped, non-empty descriptions of all phases joined by a blank line. The code incorrectly inserts a prefix (e.g., 'Phase 1 (Test): ') before each description, changing the content.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | A temporary directory |
| phases.json (phase 1) | `{"phase": 1, "name": "Analysis Phase", "description": "First phase handles initial setup", ...}` |
| phases.json (phase 2) | `{"phase": 2, "name": "Verification Phase", "description": "Second phase verifies the results", ...}` |
| phases.json (phase 3) | `{"phase": 3, "name": "Cleanup Phase", "description": "  Final phase does cleanup  ", ...}` |

### Expected (spec-correct) Output

`"First phase handles initial setup\n\nSecond phase verifies the results\n\nFinal phase does cleanup"`

### Actual (buggy) Output

`"Phase 1 (Analysis Phase): First phase handles initial setup\n\nPhase 2 (Verification Phase): Second phase verifies the results\n\nPhase 3 (Cleanup Phase): Final phase does cleanup"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.pipeline_setup import _collapse_phases_to_one

with tempfile.TemporaryDirectory() as work_dir:
    phases = {
        "phases": [
            {"phase": 1, "name": "P1", "description": "desc one", "modules": [], "depends_on_phases": []},
            {"phase": 2, "name": "P2", "description": "desc two", "modules": [], "depends_on_phases": []},
        ]
    }
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases, f)
    _collapse_phases_to_one(work_dir)
    with open(os.path.join(work_dir, "phases.json")) as f:
        result = json.load(f)
    print(result["phases"][0]["description"])
# actual (buggy) output: "Phase 1 (P1): desc one\n\nPhase 2 (P2): desc two"
# expected (correct) output: "desc one\n\ndesc two"
```

---

## Probe Script

```python
"""Probe for bug: _collapse_phases_to_one inserts "Phase N (Name): " prefix
before each phase's description instead of just joining stripped non-empty
descriptions with blank lines.

Bug ID: src--pipeline_setup-py--_collapse_phases_to_one

Expected (spec): merged description = stripped non-empty descriptions of all
phases joined by "\n\n", no prefixes.

Actual (bug): code produces "Phase 1 (Name1): desc1\n\nPhase 2 (Name2): desc2"
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def main():
    # Ensure the repo root is importable
    _REPO_ROOT = Path(__file__).resolve().parent.parent.parent
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    # --- Save and sanitize environment ---
    _saved_env = {k: os.environ.get(k) for k in (
        "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
        "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
        "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
        "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
        "FM_AGENT_DOMAIN_KNOWLEDGE",
    )}
    for k in _saved_env:
        if k in os.environ:
            del os.environ[k]

    tmpdir = None
    try:
        # --- Step 1: Create a temporary work_dir with phases.json ---
        tmpdir = tempfile.mkdtemp(prefix="probe_collapse_phases_")
        phases_path = os.path.join(tmpdir, "phases.json")

        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Analysis Phase",
                    "description": "First phase handles initial setup",
                    "modules": [
                        {"name": "mod_a", "source_files": ["a.py"]},
                    ],
                    "depends_on_phases": [],
                },
                {
                    "phase": 2,
                    "name": "Verification Phase",
                    "description": "Second phase verifies the results",
                    "modules": [
                        {"name": "mod_b", "source_files": ["b.py"]},
                    ],
                    "depends_on_phases": [1],
                },
                {
                    "phase": 3,
                    "name": "Cleanup Phase",
                    "description": "  Final phase does cleanup  ",
                    "modules": [
                        {"name": "mod_c", "source_files": ["c.py"]},
                    ],
                    "depends_on_phases": [2],
                },
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        # --- Step 2: Setup domain context files ---
        domain_dir = os.path.join(tmpdir, "spec_prompts", "domain_context")
        os.makedirs(domain_dir, exist_ok=True)
        with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
            f.write("TypeSetA from phase 1")
        with open(os.path.join(domain_dir, "phase_02_types.txt"), "w") as f:
            f.write("TypeSetB from phase 2")
        with open(os.path.join(domain_dir, "phase_03_types.txt"), "w") as f:
            f.write("TypeSetC from phase 3")
        # Also create a non-phase file that should survive
        with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
            f.write("Engine overview")

        # --- Step 3: Import and call the function under test ---
        from src.pipeline_setup import _collapse_phases_to_one
        _collapse_phases_to_one(tmpdir)

        # --- Step 4: Read back and verify ---
        with open(phases_path, "r") as f:
            result = json.load(f)

        merged_phases = result.get("phases", [])
        assert len(merged_phases) == 1, (
            f"Expected 1 merged phase, got {len(merged_phases)}"
        )
        actual_description = merged_phases[0].get("description", "")

        # Spec-correct expected: just stripped non-empty descriptions joined by "\n\n"
        expected_description = (
            "First phase handles initial setup\n\n"
            "Second phase verifies the results\n\n"
            "Final phase does cleanup"
        )

        # The bug: code prepends "Phase N (Name): " prefix
        # So actual will contain "Phase 1 (Analysis Phase): First phase..."
        # This does NOT match expected (just the raw descriptions)
        passed = actual_description != expected_description

        # --- Step 5: Verify domain context merge ---
        merged_types_path = os.path.join(domain_dir, "phase_01_types.txt")
        with open(merged_types_path, "r") as f:
            actual_types_content = f.read()

        # Check that only phase_01_types.txt remains
        remaining_types_files = [
            f for f in os.listdir(domain_dir)
            if f.startswith("phase_") and f.endswith("_types.txt")
        ]
        engine_overview_still_exists = os.path.exists(
            os.path.join(domain_dir, "engine_overview.txt")
        )

        if passed:
            print(
                f"CONFIRMED — description has unwanted phase prefix: "
                f"actual: {actual_description!r} | "
                f"expected: {expected_description!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — description matches spec: {actual_description!r}"
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(e).__name__}: {e}")

    finally:
        # Restore environment
        for k, v in _saved_env.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

        # Clean up temp directory
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — description has unwanted phase prefix: actual: 'Phase 1 (Analysis Phase): First phase handles initial setup\n\nPhase 2 (Verification Phase): Second phase verifies the results\n\nPhase 3 (Cleanup Phase): Final phase does cleanup' | expected: 'First phase handles initial setup\n\nSecond phase verifies the results\n\nFinal phase does cleanup'
```
