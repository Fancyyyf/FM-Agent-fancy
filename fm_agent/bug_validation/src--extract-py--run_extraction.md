# Bug Report: run_extraction

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/extract-py/run_extraction.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple (written, skipped) where both are non-negative integers. written is the number of function extraction files newly created; skipped is the number of function files that already existed with valid .spec.json and .info.json sidecars and were left unchanged.

Every written file resides under work_dir/extracted_functions/ (falling back to proj_dir/extracted_functions/) and follows the path convention <source_rel_dir>/<basename-ext>/<func_name>.<ext>, where <basename-ext> replaces the last dot in the source filename with a hyphen.

Each written file contains the extracted source code of exactly one function. A file matching an existing, fully-specced function (both .spec.json and .info.json sidecars present and valid) is NOT written unless force is True.

Source files whose relative path matches test-file patterns, or whose extension maps to no known language handler, are excluded from extraction.

When both written and skipped are zero (no source files produced any extractable function), an error-level log message is emitted.

If phases.json is absent from the expected location, FileNotFoundError is raised.

---

### Actual Behavior

The function returns a tuple (written_count, skipped_count). After normal execution, for every relative path `sf` that appears in `phases.json` under any phase's modules' `source_files`, if `sf` is not a test file (according to `_is_test_file`) and the absolute path `os.path.join(proj_dir, sf)` exists, then all functions extracted from that file (using the pre-built `registry_funcs` mapping normalized absolute paths to function lists, or via `extract_functions_from_file` if languagespecific reextraction is needed) are processed. For each function, a safe filename is generated and the output file `<work_dir>/extracted_functions/<safe_filename>` is created or overwritten. If `force` is `False` and the output file already exists and is valid (both `.spec.json` and `.info.json` sidecars present, i.e., `is_file_ready` returns `True`), the function is skipped and counted in `skipped_count`; otherwise the function body is written, sidecars are produced, and it is counted in `written_count`. After all source files are processed, the output directory is validated via `_validate_extraction`; any extracted file containing a number of functions different from one is reported (e.g., logged), but does not affect the returned counts. If `verbose` is `True`, informational messages are printed. If the precondition that `phases.json` exists and is valid JSON is violated, `FileNotFoundError` or `json.JSONDecodeError` is raised before any side effects. Missing source files trigger a warning and are skipped without contributing to any count. No files outside `work_dir/extracted_functions/` are modified.

---

## Code Evidence

The code block does not include the lines that construct the output file path, but the overall behavior (condition A) writes `<work_dir>/extracted_functions/<safe_filename>` without subdirectories, violating the required path convention.

---

## Trigger Condition

Every written file must follow the path convention <source_rel_dir>/<basename-ext>/<func_name>.<ext>, but the code generates only a safe filename placed directly under the output base, resulting in a flat structure.

---

## How to trigger the bug

The probe created a minimal test project with a source file `mypkg/utils.py` containing two functions (`add` and `sub`). After running `run_extraction`, the output files were inspected.

The actual source code at `src/extract.py` lines 724-731 clearly constructs the output directory path using `src_dir` (the relative directory of the source file) and `dir_name` (basename with last dot replaced by hyphen), then line 755 joins the safe function filename under that directory. This yields paths following the `<source_rel_dir>/<basename-ext>/<func_name>.<ext>` convention exactly.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `<tempdir>` |
| work_dir | `<tempdir>` |
| force | True |
| phases.json | `{"phases": [{"modules": [{"source_files": ["mypkg/utils.py"]}]}]}` |
| Source file | `mypkg/utils.py` with functions `add` and `sub` |

### Expected (spec-correct) Output

Files at:
- `mypkg/utils-py/add.py`
- `mypkg/utils-py/sub.py`

### Actual (buggy) Output

Files at:
- `mypkg/utils-py/add.py`
- `mypkg/utils-py/sub.py`

The actual output matches the spec-correct output. The code DOES follow the path convention.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile
tmpdir = tempfile.mkdtemp()
os.makedirs(os.path.join(tmpdir, "mypkg"), exist_ok=True)
with open(os.path.join(tmpdir, "mypkg", "utils.py"), "w") as f:
    f.write("def add(x, y):\n    return x + y\n\ndef sub(x, y):\n    return x - y\n")
with open(os.path.join(tmpdir, "phases.json"), "w") as f:
    json.dump({"phases": [{"modules": [{"source_files": ["mypkg/utils.py"]}]}]}, f)

from src.extract import run_extraction
written, skipped = run_extraction(tmpdir, tmpdir, force=True, verbose=False)
# Output files: tmpdir/extracted_functions/mypkg/utils-py/{add,sub}.py
# These follow the <source_rel_dir>/<basename-ext>/<func_name>.<ext> convention
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# All test fixtures, outputs, and intermediate files live under a temp dir.
# We import from the repo's source tree but never use the repo workspace for I/O.
tmpdir = tempfile.mkdtemp(prefix="probe_run_extraction_")

# -------------------------------------------------------------------
# 1. Create a minimal test project inside the temp directory
# -------------------------------------------------------------------
# Source file: mypkg/utils.py with two functions
test_src_dir = os.path.join(tmpdir, "mypkg")
os.makedirs(test_src_dir, exist_ok=True)
test_src_file = os.path.join(test_src_dir, "utils.py")
with open(test_src_file, "w") as f:
    f.write("def add(x, y):\n    return x + y\n\ndef sub(x, y):\n    return x - y\n")

# phases.json referencing that source file
phases = {"phases": [{"modules": [{"source_files": ["mypkg/utils.py"]}]}]}
phases_path = os.path.join(tmpdir, "phases.json")
with open(phases_path, "w") as f:
    json.dump(phases, f)

# -------------------------------------------------------------------
# 2. Call run_extraction via the public entry point
# -------------------------------------------------------------------
# The repo root must be on sys.path so 'from src.extract import run_extraction'
# resolves. We add it at the front so intra-package 'from src.xxx' imports work.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from src.extract import run_extraction

    written, skipped = run_extraction(
        proj_dir=tmpdir,
        work_dir=tmpdir,
        force=True,
        verbose=False,
    )
except Exception as e:
    # Catch import errors, codegraph failures, etc.
    print(f"ERROR: {e}", file=sys.stderr)
    # Still write the verdict marker
    print("NOT CONFIRMED")
    sys.exit(0)

# -------------------------------------------------------------------
# 3. Inspect the output paths
# -------------------------------------------------------------------
output_base = os.path.join(tmpdir, "extracted_functions")

convention_paths = []  # paths following <source_rel_dir>/<basename-ext>/<func_name>.<ext>
flat_paths = []        # paths directly under extracted_functions/ with no subdirs
other_paths = []       # anything else

for root, _dirs, files in os.walk(output_base):
    for fname in files:
        full = os.path.join(root, fname)
        rel = os.path.relpath(full, output_base)
        parts = rel.split(os.sep)
        if len(parts) == 3:
            convention_paths.append(rel)
        elif len(parts) == 1:
            flat_paths.append(rel)
        else:
            other_paths.append(rel)

# The bug claim: files are written flat (no subdirectories).
# If we find convention paths, the bug is NOT CONFIRMED.
# If files are flat, the bug IS CONFIRMED.
bug_confirmed = len(convention_paths) == 0 and len(flat_paths) > 0

if bug_confirmed:
    print(f"CONFIRMED - flat files detected (no subdirectory structure)")
    print(f"Flat paths: {flat_paths}")
else:
    print(f"NOT CONFIRMED - output files follow path convention")
    print(f"Convention paths found: {convention_paths}")
    if flat_paths:
        print(f"Flat paths also present: {flat_paths}")
    if other_paths:
        print(f"Other paths: {other_paths}")

# Cleanup temp dir
shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
Extraction complete: 2 written, 0 skipped.
NOT CONFIRMED - output files follow path convention
Convention paths found: ['mypkg/utils-py/add.py', 'mypkg/utils-py/sub.py']
```
