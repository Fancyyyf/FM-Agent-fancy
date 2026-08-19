# Bug Report: _sync_domain_context

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For every phase number in changed_phases that still owns at least one source file according to the current phases.json, the phase_NN_types.txt file under work_dir/spec_prompts/domain_context/ is regenerated to reflect the source files and their associated types and invariants as defined in the current phases.json. If a phase number in changed_phases no longer owns any source file, no types file is regenerated for that phase. If a phase-cleanup renumbering or removal is present and indicates structural changes (a phase was removed or renumbered to a different number), engine_overview.txt is also regenerated. If no changed phase has remaining source files and no structural cleanup change is detected, the function returns immediately without modifying any domain-context files. Regeneration is attempted up to a configured maximum number of retries; if all attempts fail, the function returns after logging a warning but does not terminate the process.

---

### Actual Behavior

Natural language: The function synchronises perphase domaincontext files. If the directory `{work_dir}/spec_prompts/domain_context/` does not exist, or if `changed_phases` is empty and `cleanup_changed` is false (i.e. no phase renumbering or removal), the function returns immediately without modifying the filesystem. Otherwise it reads the current sourcefile assignment from `phases.json` and selects for regeneration only those changed phases that still own at least one source file (`regenerate`). If `regenerate` is nonempty or `cleanup_changed` is true, an LLM agent is invoked with a prompt describing the phases to regenerate and any renumbering/removal context. On successful completion, for every phase number `p` in `regenerate` the file `phase_{p}_types.txt` exists in the domaincontext directory and its content is consistent with the source files recorded for phase `p` in `phases.json`, and any renumbering or removal of phases described in `phase_cleanup` has been applied to the domaincontext files as instructed. If the LLM command fails, a `subprocess.CalledProcessError` is raised and no promise about file state is made. If no agent is invoked (`regenerate` empty and `cleanup_changed` false) the function simply returns with no effect. Formal logic: let WD = work_dir, DC = WD/spec_prompts/domain_context/. After a normal return without exception one of the following holds: (1) dir(DC)  (changed_phases =   cleanup_changed)  filesystem unchanged. (2) dir(DC)  (changed_phases    cleanup_changed)  let SF = _phase_source_files(WD/phases.json) in let R = { p : SF[p] | pchanged_phases  SF[p][] } in ( (R=  cleanup_changed)  unchanged )  ( (R  cleanup_changed)  run_opencode_traced succeeds  pR: file(DC/phase_{p}_types.txt) exists  content_consistent(p, SF[p], phase_cleanup)  cleanup_applied_in(DC, phase_cleanup) ). If run_opencode_traced raises CalledProcessError the exception propagates and the above poststate is not guaranteed.

---

## Code Evidence

Line 31: if not os.path.isdir(domain_dir):
Line 32: logging.info("No domain_context/ directory to sync after phase edits; skipping.")
Line 33: return

---

## Trigger Condition

The specification requires that for every phase number in changed_phases that still owns at least one source file, the corresponding phase_NN_types.txt file is regenerated. It does not provide an exception when the domain_context directory is missing. The code, however, returns early without regenerating any file when the directory does not exist (Lines 31-33). This missing-case rejection violates the specification.

---

## How to trigger the bug

The function `_sync_domain_context` in `src/pipeline_setup.py` checks if `work_dir/spec_prompts/domain_context/` exists (line 184). When it does not, the function logs an info message and returns immediately (lines 185-186), even when `changed_phases` contains phase numbers that still own source files in `phases.json`. The specification does not permit this early return — it requires regeneration for every changed phase with source files regardless of whether the directory currently exists.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/fake_proj_dir` |
| `work_dir` | `<tempdir>` (contains valid `phases.json` with phase 1 owning `["test.py"]`) |
| `changed_phases` | `{1}` |
| `phase_cleanup` | `None` (no renumbering/removal) |
| Directory `work_dir/spec_prompts/domain_context/` | does NOT exist |

### Expected (spec-correct) Output

The function should proceed past the directory check and attempt to regenerate `phase_01_types.txt` by invoking the LLM agent via `run_opencode_traced`. It may create the directory if needed or fail with an error, but it should not silently skip regeneration.

### Actual (buggy) Output

The function returns immediately at line 186 without calling `run_opencode_traced`. No `phase_01_types.txt` is regenerated. The log message "No domain_context/ directory to sync after phase edits; skipping." is written.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, json
from unittest.mock import patch
from src.pipeline_setup import _sync_domain_context

with tempfile.TemporaryDirectory() as work_dir:
    # Create a valid phases.json with phase 1 owning a source file
    phases = {
        "phases": [{
            "phase": 1,
            "name": "Test Phase",
            "modules": [{"name": "m", "source_files": ["test.py"]}],
            "depends_on_phases": [],
        }]
    }
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases, f)

    # DO NOT create spec_prompts/domain_context/ directory

    called = [False]
    def fake_traced(*a, **kw):
        called[0] = True

    with patch("src.pipeline_setup.run_opencode_traced", fake_traced), \
         patch("src.pipeline_setup.build_llm_cli_command", return_value=["echo"]), \
         patch("src.pipeline_setup.OPENCODE_SETUP_MODEL", "mocked"), \
         patch("src.pipeline_setup.OPENCODE_MAX_RETRIES", 1):
        _sync_domain_context("/tmp/fake", work_dir, {1})

    # actual (buggy) output: called[0] is False (early return, no regeneration)
    # expected (correct) output: called[0] is True (regeneration was attempted)
```

---

## Probe Script

```python
"""Probe for bug: _sync_domain_context returns early when domain_context/ is missing.

Bug: The spec requires regeneration of phase_NN_types.txt for every changed phase
that still owns source files, with no exception for a missing domain_context directory.
The code (lines 184-186) returns early without regeneration when the directory does not exist.
"""
import sys
import os
import json
import tempfile
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def main():
    try:
        # Set up logging to suppress info messages
        logging.basicConfig(level=logging.WARNING)

        from src.pipeline_setup import _sync_domain_context

        # -------------------------------------------------------------------
        # Create a temporary work_dir with a valid phases.json but NO domain_context dir
        # -------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as work_dir:
            phases = {
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test Phase",
                        "description": "A test phase for probing the bug.",
                        "modules": [
                            {
                                "name": "test_module",
                                "description": "Test module",
                                "source_files": ["test.py"],
                            }
                        ],
                        "depends_on_phases": [],
                    }
                ]
            }
            phases_json_path = os.path.join(work_dir, "phases.json")
            with open(phases_json_path, "w") as f:
                json.dump(phases, f, indent=2)

            # Explicitly ensure the domain_context directory does NOT exist
            domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
            if os.path.exists(domain_dir):
                import shutil
                shutil.rmtree(domain_dir)
            # Also ensure the parent spec_prompts doesn't exist
            spec_prompts = os.path.join(work_dir, "spec_prompts")
            if os.path.exists(spec_prompts):
                import shutil
                shutil.rmtree(spec_prompts)

            # -------------------------------------------------------------------
            # Patch run_opencode_traced to detect if it gets called
            # -------------------------------------------------------------------
            opcode_called = [False]

            def fake_run_opencode_traced(*args, **kwargs):
                opcode_called[0] = True

            # Also patch build_llm_cli_command in case we slip past the guard
            fake_command = ["echo", "mocked"]

            with patch(
                "src.pipeline_setup.run_opencode_traced", fake_run_opencode_traced
            ), patch(
                "src.pipeline_setup.build_llm_cli_command", return_value=fake_command
            ), patch(
                "src.pipeline_setup.OPENCODE_SETUP_MODEL", "mocked-model"
            ), patch(
                "src.pipeline_setup.OPENCODE_MAX_RETRIES", 1
            ):
                _sync_domain_context(
                    proj_dir="/tmp/fake_proj_dir",
                    work_dir=work_dir,
                    changed_phases={1},
                )

            # -------------------------------------------------------------------
            # Verify result
            # -------------------------------------------------------------------
            if opcode_called[0]:
                print(
                    "NOT CONFIRMED — "
                    "run_opencode_traced was called, meaning _sync_domain_context "
                    "did NOT return early when domain_context/ directory is missing. "
                    "The spec-required regeneration was attempted."
                )
            else:
                print(
                    "CONFIRMED — "
                    "_sync_domain_context returned early without calling "
                    "run_opencode_traced when domain_context/ directory is missing, "
                    "even though phase 1 in changed_phases still owns source files. "
                    "This mismatches the spec which requires regeneration with no "
                    "exception for a missing directory."
                )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — _sync_domain_context returned early without calling run_opencode_traced when domain_context/ directory is missing, even though phase 1 in changed_phases still owns source files. This mismatches the spec which requires regeneration with no exception for a missing directory.
```
