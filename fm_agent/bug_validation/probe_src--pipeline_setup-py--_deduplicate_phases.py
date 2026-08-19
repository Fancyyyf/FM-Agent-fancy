#!/usr/bin/env python3
"""Probe for bug src--pipeline_setup-py--_deduplicate_phases.

Spec contract of src.pipeline_setup._deduplicate_phases(phases_dir):
  "The function returns a dict containing a 'modified_modules' key whose value
   is a list holding one entry per module that lost at least one duplicate
   file; ... The list is empty exactly when the plan already had no duplicate
   source file."

Trigger: a module whose source_files list contains the same file twice
(an intra-module duplicate). The deduplication loop keeps the first
occurrence (added to `seen` and `deduped`) and drops the later one from the
module's source_files, which is rewritten to phases.json. But the
removed_files computation

    removed_files = [sf for sf in original if sf not in deduped]

tests membership against `deduped`, where the first kept occurrence of the
file still exists. Every occurrence therefore fails the `not in` test,
`removed_files` is empty, the `if removed_files:` guard is False, and the
module is never appended to `changed_modules`. The returned
`modified_modules` list is empty even though a duplicate file WAS removed
from the plan on disk, violating the spec.

FM-Agent self-validation guard compliance:
- No FM-Agent workflow is started: no run_pipeline(), run_incremental_
  pipeline(), main.py, FM-Agent CLI, OpenCode, or subprocess is invoked.
  Only the smallest relevant unit, _deduplicate_phases, is called with a
  fixture. It performs no LLM/OpenCode work — only JSON file I/O.
- All fixtures and runtime outputs live under a fresh temporary directory
  owned by the probe; nothing is read from or written to the active
  repository or its fm_agent/ directory, apart from loading project modules.
- The module is loaded through the package import (`src.pipeline_setup`),
  which starts no workflow.
"""

import json
import os
import shutil
import sys
import tempfile

BUG_ID = "src--pipeline_setup-py--_deduplicate_phases"

# Probe lives at <repo_root>/fm_agent/bug_validation/probe_<bug_id>.py; the
# repo root is two levels up. Make the package importable regardless of cwd.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def main():
    work = tempfile.mkdtemp(prefix="fm_probe_" + BUG_ID + "_")
    try:
        from src.pipeline_setup import _deduplicate_phases

        # Fixture: one phase with two modules. 'mod_dup' owns the same
        # source file twice (intra-module duplicate) plus one unique file;
        # 'mod_plain' is duplicate-free.
        plan = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Phase One",
                    "description": "Initial phase.",
                    "depends_on_phases": [],
                    "modules": [
                        {
                            "name": "mod_dup",
                            "description": "Module with an intra-module duplicate.",
                            "source_files": ["src/a.py", "src/a.py", "src/b.py"],
                        },
                        {
                            "name": "mod_plain",
                            "description": "Duplicate-free module.",
                            "source_files": ["src/c.py"],
                        },
                    ],
                }
            ]
        }
        phases_path = os.path.join(work, "phases.json")
        with open(phases_path, "w") as f:
            json.dump(plan, f, indent=2)

        actual = _deduplicate_phases(work)

        with open(phases_path, "r") as f:
            on_disk = json.load(f)
        disk_mod_dup = on_disk["phases"][0]["modules"][0]["source_files"]

        # Precondition: deduplication really did strip the later occurrence
        # of 'src/a.py' from phases.json on disk, i.e. module 'mod_dup'
        # lost a duplicate file. Without this the trigger was not reached.
        if disk_mod_dup != ["src/a.py", "src/b.py"]:
            print(
                "ERROR: precondition not reached - on-disk source_files of "
                f"'mod_dup' are {disk_mod_dup!r}, expected ['src/a.py', 'src/b.py']"
            )
            return 1

        # Spec (oracle): one modified_modules entry per module that lost at
        # least one duplicate file; the list is empty exactly when the plan
        # had no duplicates. The plan had exactly one duplicate ('src/a.py'
        # in 'mod_dup'), so exactly one entry reporting it is required.
        expected = {
            "modified_modules": [
                {
                    "phase": 1,
                    "module": "mod_dup",
                    "removed_files": ["src/a.py"],
                    "source_files": ["src/a.py", "src/b.py"],
                }
            ]
        }

        passed = actual != expected  # True -> bug reproduced
    except Exception as e:  # noqa: BLE001 - probe must catch everything
        print(f"ERROR: {type(e).__name__}: {e}")
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
            "(the plan contained the intra-module duplicate 'src/a.py' in "
            "module 'mod_dup'; deduplication stripped its later occurrence "
            "from phases.json on disk, so the spec requires one "
            "modified_modules entry for 'mod_dup', but the returned list "
            f"is {actual.get('modified_modules')!r})"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
