# Bug Report: _deduplicate_phases

**Source file:** `/tmp/fm_agent_wt_FM-Agent_jx75d3w8/snapshot/fm_agent/extracted_functions/src/pipeline_setup-py/_deduplicate_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

After return, the phases.json on disk in phases_dir contains the same plan as before except that no source file is owned anywhere in the plan more than once: for every source file, its earliest occurrence in plan order (phases in ascending "phase" number, then modules in listed order, then files in listed order) is kept and every later occurrence is removed from the source_files list of the module that held it. The order of the retained files inside each module is preserved, no file is added anywhere, and the file written to disk is a JSON document readable by the same schema. Nothing besides source_files lists is changed: every phase and every module remains present with its number, name, description, and depends_on_phases intact even if its source_files list becomes empty, so phase numbering stays aligned with already-produced per-phase artifacts. The function returns a dict containing a "modified_modules" key whose value is a list holding one entry per module that lost at least one duplicate file; each entry records that module's phase number (the same numbering as in the freshly written phases.json), its name, the files removed from it, and its remaining source files. The list is empty exactly when the plan already had no duplicate source file.

---

### Actual Behavior

Upon normal termination: (1) The file at os.path.join(phases_dir, 'phases.json') has been overwritten (via json.dump with indent=2) with a JSON object whose structure mirrors the original plan except that every module's 'source_files' list has been filtered. (2) Deduplication invariant: for every source-file string sf that appeared anywhere in the original plan, sf appears in the 'source_files' list of exactly one module in the written JSON  specifically the module belonging to the phase with the smallest 'phase' number (and, within that phase, the earliest module iteration order) that originally contained sf. No source file appears in more than one module's 'source_files' in the output. (3) Structural preservation: the set of phases (identified by their 'phase' integer) and the set of modules within each phase are identical to those in the input; no phase or module object is added or removed. Phase numbers and all keys other than 'source_files' are unchanged. A module whose 'source_files' becomes empty is still present. (4) Return value: a dict with a single key 'modified_modules' mapping to a list of dicts. Each entry corresponds to one module whose 'source_files' list shrank (i.e., at least one file was removed) and contains: 'phase' (int, the phase number), 'module' (str, the module's 'name' or '' if absent), 'removed_files' (list of str, the source-file paths stripped from that module), and 'source_files' (list of str, the module's source_files after deduplication). Modules that lost no files are absent from this list. The list is ordered by ascending phase number then original module iteration order. (5) The global set 'seen' at termination equals the union of all 'source_files' lists across all modules in the written JSON (equivalently, the set of all distinct source-file strings from the original plan). Upon abnormal termination: if phases_dir/phases.json cannot be opened for reading, a FileNotFoundError or PermissionError propagates; if its content is not valid JSON, a json.JSONDecodeError propagates; if the parsed object lacks a 'phases' key or any phase lacks 'phase'/'modules' or any module lacks 'source_files', a KeyError or TypeError propagates. In all exception cases the file on disk is unmodified (the write at line 37 is never reached) and no value is returned.

---

## Code Evidence

Line 32: removed_files = [sf for sf in original if sf not in deduped]

---

## Trigger Condition

When a source file appears more than once within the same module, the deduplication correctly removes the later occurrences from source_files, but the removed_files computation on Line 32 uses membership testing against the deduped list. Since the file string still exists in deduped (from its first kept occurrence), the list comprehension yields an empty list. Consequently, the `if removed_files:` guard on Line 33 is False, the module is never appended to changed_modules, and it is absent from the returned modified_modules list. The specification requires one entry per module that lost at least one duplicate file and mandates the list is empty only when no duplicates existed in the plan.

---

## How to trigger the bug

The probe builds a phases.json fixture (in a fresh temporary directory) containing a single phase whose module `mod_dup` owns the same source file `src/a.py` twice, plus a unique file `src/b.py`. During deduplication, the first occurrence of `src/a.py` is added to `seen` and kept in `deduped`; the second occurrence is correctly dropped, so the module's `source_files` on disk shrinks from `["src/a.py", "src/a.py", "src/b.py"]` to `["src/a.py", "src/b.py"]`. However, `removed_files = [sf for sf in original if sf not in deduped]` tests membership against `deduped`, which still contains `src/a.py` from its first kept occurrence. Every occurrence of `src/a.py` in `original` therefore fails the `not in` test, `removed_files` evaluates to `[]`, the `if removed_files:` guard is False, and `mod_dup` is never appended to `changed_modules`. The function returns `{"modified_modules": []}` even though the plan contained a duplicate and the module did lose a file on disk. The specification requires exactly one `modified_modules` entry for `mod_dup` and mandates the list is empty only when the plan had no duplicates.

Note: cross-module duplicates (a file claimed by a later module) are reported correctly, because in that case the file is absent from the later module's `deduped` list entirely; the bug is specific to duplicates within the same module's `source_files` list.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_dir` | fresh temporary directory containing the `phases.json` fixture below |
| `phases.json` content | 1 phase (`"phase": 1`, name `"Phase One"`) with modules `mod_dup` (`source_files`: `["src/a.py", "src/a.py", "src/b.py"]`) and `mod_plain` (`source_files`: `["src/c.py"]`) |
| Intra-module duplicate | `"src/a.py"` appears twice in `mod_dup.source_files` |

### Expected (spec-correct) Output

`{'modified_modules': [{'phase': 1, 'module': 'mod_dup', 'removed_files': ['src/a.py'], 'source_files': ['src/a.py', 'src/b.py']}]}`

### Actual (buggy) Output

`{'modified_modules': []}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually (FM-Agent self-validation guard: only the smallest unit is exercised — no FM-Agent workflow, `run_pipeline()`, `main.py`, CLI, or OpenCode is started):

1. Navigate to the repo root.
2. Run the following snippet (loads the project module via the package import and uses a fixture in a fresh temp dir):

```python
import json, os, tempfile
from src.pipeline_setup import _deduplicate_phases

work = tempfile.mkdtemp()
plan = {"phases": [{
    "phase": 1, "name": "Phase One", "description": "Initial phase.",
    "depends_on_phases": [],
    "modules": [
        {"name": "mod_dup", "description": "Module with an intra-module duplicate.",
         "source_files": ["src/a.py", "src/a.py", "src/b.py"]},
        {"name": "mod_plain", "description": "Duplicate-free module.",
         "source_files": ["src/c.py"]},
    ],
}]}
with open(os.path.join(work, "phases.json"), "w") as f:
    json.dump(plan, f)

result = _deduplicate_phases(work)
print(result)
# actual (buggy) output: {'modified_modules': []}
# expected (correct) output: {'modified_modules': [{'phase': 1, 'module': 'mod_dup', 'removed_files': ['src/a.py'], 'source_files': ['src/a.py', 'src/b.py']}]}
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: {'modified_modules': []} | expected: {'modified_modules': [{'phase': 1, 'module': 'mod_dup', 'removed_files': ['src/a.py'], 'source_files': ['src/a.py', 'src/b.py']}]} (the plan contained the intra-module duplicate 'src/a.py' in module 'mod_dup'; deduplication stripped its later occurrence from phases.json on disk, so the spec requires one modified_modules entry for 'mod_dup', but the returned list is [])
```
