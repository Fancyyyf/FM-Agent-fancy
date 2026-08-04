# Bug Report: _phases_cover_current_sources

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True if and only if all of the following hold: (1) the file at phases_json exists, is readable, and contains valid JSON whose 'phases' key holds a list that includes at least one source file path across all modules; (2) every source file path listed under 'phases' is a normalized forward-slash path that corresponds to an existing file relative to proj_dir; (3) when submodules is not None, every listed source file path falls under at least one of the specified submodule directories; (4) the set of all source file paths listed in the phases plan is a superset of the set of project source files collected from proj_dir, scoped to submodules when provided. Returns False if any condition fails, including when the phases.json file cannot be opened or contains non-JSON content.

---

### Actual Behavior

Upon return, the function returns a boolean value. If an OSError or ValueError occurs while opening or parsing the file at phases_json, the function returns False and no side effects persist. Otherwise, let listed be the set of paths obtained by iterating over data.get('phases', [])phase.get('modules', [])module.get('source_files', []) and replacing each backslash '\' with forward slash '/'. If listed is empty, the function returns False. If submodules is not None and for some sf in listed, _is_under_submodules(sf, submodules) is False, the function returns False. If there exists sf in listed such that os.path.join(proj_dir, sf) does not exist on the file system, the function returns False. Otherwise, the function returns the result of _collect_project_source_files(proj_dir, submodules).issubset(listed). Thus the final return value is True if and only if (i) the JSON file was successfully loaded, (ii) listed is non-empty, (iii) when submodules is provided, every listed source file is under a submodule directory, (iv) every listed source file exists relative to proj_dir, and (v) every actual source file discoverable under proj_dir (restricted to submodules if submodules is not None) is mentioned in listed.

---

## Code Evidence

Line 11: for source_file in module.get("source_files", []):
Line 12:                 listed.add(source_file.replace("\\", "/"))

---

## Trigger Condition

The specification requires every listed source file path to be a normalized forward-slash path. The code only replaces backslashes with forward slashes and does not reject non-normalized paths like empty strings or paths with double slashes. This allows an empty string to be accepted as a listed path, leading to a True return when the JSON is invalid per the specification.

---

## How to trigger the bug

The function `_phases_cover_current_sources` at `src/pipeline_setup.py:731` performs path validation at line 742 with only `source_file.replace("\\", "/")`. For an empty-string `source_file`, `replace("\\", "/")` yields `""`. The existence check at line 749 uses `os.path.join(proj_dir, sf)` — and `os.path.join(proj_dir, "")` equals `proj_dir`, which always exists. The empty string therefore passes all checks, allowing the function to return `True` when the spec requires `False` (since `""` is not a "normalized forward-slash path").

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | path to a JSON file containing `"source_files": ["dummy.py", ""]` |
| `proj_dir` | a directory containing `dummy.py` (a valid .py source file) |

### Expected (spec-correct) Output

`False` — per spec condition (2), every listed path must be a normalized forward-slash path, and `""` is not one.

### Actual (buggy) Output

`True` — `""` passes `replace("\\", "/")` unchanged, `os.path.join(proj_dir, "")` resolves to `proj_dir` (which exists), and the listed set is a superset of the discovered source files.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.pipeline_setup import _phases_cover_current_sources

tmpdir = tempfile.mkdtemp()
open(os.path.join(tmpdir, "dummy.py"), "w").close()
phases = os.path.join(tmpdir, "phases.json")
json.dump({"phases": [{"modules": [{"source_files": ["dummy.py", ""]}]}]}, open(phases, "w"))
result = _phases_cover_current_sources(phases, tmpdir)
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe script for bug: _phases_cover_current_sources accepts empty-string source_file paths.

Bug ID: src--pipeline_setup-py--_phases_cover_current_sources

The specification requires every listed source file path to be a normalized
forward-slash path. The code only replaces backslashes with forward slashes and
does not reject non-normalized paths like empty strings, allowing an empty string
to pass the existence check (os.path.join(proj_dir, "") == proj_dir, which exists).

This probe creates a temporary directory with a valid .py source file, writes a
phases.json that includes both the valid file AND an empty string source_file, then
calls _phases_cover_current_sources to check whether the function incorrectly
returns True despite the non-normalized empty-string path.
"""

import json
import os
import sys
import tempfile

# Add repo root to path so 'config' and 'src' are importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.pipeline_setup import _phases_cover_current_sources
except ImportError as e:
    print(f"ERROR: Could not import _phases_cover_current_sources: {e}")
    sys.exit(1)


def run_probe():
    """Create temp fixtures and test the bug."""
    tmpdir = tempfile.mkdtemp(prefix="bug_validator_probe_")

    try:
        # 1. Create a dummy .py source file so _collect_project_source_files
        #    discovers it via _iter_project_source_files (which filters by
        #    EXT_TO_LANG from src.extract).
        dummy_py = os.path.join(tmpdir, "dummy.py")
        with open(dummy_py, "w") as f:
            f.write("# dummy source file for bug probe\n")

        # 2. Create phases.json that lists:
        #    - the valid source file "dummy.py"
        #    - an empty string "" as a non-normalized path
        phases_path = os.path.join(tmpdir, "phases.json")
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Test Phase",
                    "description": "Probe phase",
                    "modules": [
                        {
                            "name": "test_module",
                            "description": "Probe module with buggy empty-string source_file",
                            "source_files": ["dummy.py", ""]
                        }
                    ],
                    "depends_on_phases": []
                }
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        # 3. Call _phases_cover_current_sources
        #    Spec says: returns False because "" is not a normalized path
        #    Code bug:  returns True because "" passes all checks
        actual = _phases_cover_current_sources(phases_path, tmpdir)

        # 4. Determine expected (spec-correct) value
        #    Per spec condition (2): "every source file path listed under
        #    'phases' is a normalized forward-slash path that corresponds to
        #    an existing file relative to proj_dir"
        #    An empty string is NOT a normalized forward-slash path.
        expected = False

        # Bug is CONFIRMED if actual != expected (code behaves against spec)
        passed = actual != expected

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    run_probe()
```

### Probe Output

```
CONFIRMED — actual: True | expected: False
```
