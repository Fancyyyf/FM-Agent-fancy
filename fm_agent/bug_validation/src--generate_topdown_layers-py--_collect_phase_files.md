# Bug Report: _collect_phase_files

**Source file:** `src/generate_topdown_layers-py/_collect_phase_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of (file_path, module_name) pairs, where module_name is the "name" of a module in phase_data
  - For each source file declared in a module: the source file's basename extension is stripped by replacing the last "." with "-" (e.g., "loader.cpp"  "loader-cpp"), and the resulting directory name is resolved under proj_dir/extracted_functions/ alongside the source file's parent directory
  - Every regular file found in such a directory is collected into the result, each paired with the name of the module that declared the source file
  - Directories that do not exist on disk are skipped with no error raised
  - Returns an empty list when phase_data has no "modules" key, the modules list is empty, or no extracted-function directories exist on disk
  - The returned list preserves no guaranteed ordering across calls

---

### Actual Behavior

The function returns a list `results` with no side effects. For every module dictionary `mod` in `phase_data.get('modules', [])` (in iteration order), let `mn = mod['name']`. For every source file path `sf` in `mod.get('source_files', [])` (in iteration order), compute: `base = os.path.basename(sf)`; `last_dot = base.rfind('.')`; `dir_name = base[:last_dot] + '-' + base[last_dot+1:]` if `last_dot > 0` else `base`; `func_dir = os.path.join(proj_dir, 'extracted_functions', os.path.dirname(sf), dir_name)` if `os.path.dirname(sf)` else `os.path.join(proj_dir, 'extracted_functions', dir_name)`. If `os.path.isdir(func_dir)` evaluates to `True`, then for every filename `fn` in the arbitrary order returned by `os.listdir(func_dir)`, if `os.path.isfile(os.path.join(func_dir, fn))` evaluates to `True`, the tuple `(os.path.join(func_dir, fn), mn)` appears in `results`. No other tuples are present. Formal post-condition:

results = [ (os.path.join(func_dir, fn), mod['name'])
            for mod in phase_data.get('modules', [])
            for sf in mod.get('source_files', [])
            let base = os.path.basename(sf)
            let last_dot = base.rfind('.')
            let dir_name = (base[:last_dot] + '-' + base[last_dot+1:]) if last_dot > 0 else base
            let func_dir = os.path.join(proj_dir, 'extracted_functions', os.path.dirname(sf), dir_name) if os.path.dirname(sf) else os.path.join(proj_dir, 'extracted_functions', dir_name)
            if os.path.isdir(func_dir)
            for fn in os.listdir(func_dir)
            if os.path.isfile(os.path.join(func_dir, fn)) ]

with the outer loops preserving the modules and source files order, and the innermost loop following the arbitrary order of `os.listdir`. The input arguments `proj_dir` and `phase_data` remain unchanged.

---

## Code Evidence

Line 14: if last_dot > 0:

---

## Trigger Condition

The specification requires replacing the last '.' with '-' unconditionally, but the code's condition (last_dot > 0) skips replacement when the last dot is at position 0 (leading dot). This causes the code to look for a directory named '.hiddenfile' instead of '-hiddenfile', missing files that should be collected.

---

## How to trigger the bug

When a source file basename begins with a dot (e.g., `.hiddenfile`), `rfind('.')` returns 0. The guard `if last_dot > 0` evaluates to `False`, so the code falls through to `dir_name = src_base`, keeping the leading dot. The function then looks for `extracted_functions/.hiddenfile/` instead of the spec-correct `extracted_functions/-hiddenfile/`. Any extracted functions placed in the spec-correct directory are silently missed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory containing `extracted_functions/-hiddenfile/some_func.py` |
| `phase_data` | `{"modules": [{"name": "test_module", "source_files": [".hiddenfile"]}]}` |

### Expected (spec-correct) Output

`[("/tmp/.../extracted_functions/-hiddenfile/some_func.py", "test_module")]` — one file collected

### Actual (buggy) Output

`[]` — empty list; the function looks in `extracted_functions/.hiddenfile/` which does not exist, so no files are collected

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, sys
sys.path.insert(0, os.getcwd())
from src.generate_topdown_layers import _collect_phase_files

proj_dir = tempfile.mkdtemp()
correct_dir = os.path.join(proj_dir, "extracted_functions", "-hiddenfile")
os.makedirs(correct_dir)
with open(os.path.join(correct_dir, "some_func.py"), "w") as f:
    f.write("# content\n")

result = _collect_phase_files(proj_dir, {
    "modules": [{"name": "test_module", "source_files": [".hiddenfile"]}]
})
print(result)
# actual (buggy) output: []
# expected (correct) output: [('/tmp/.../extracted_functions/-hiddenfile/some_func.py', 'test_module')]
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

# Ensure the project root is on sys.path so the src package resolves.
# The script is meant to be run from repo root, so os.getcwd() is the repo root.
sys.path.insert(0, os.getcwd())

try:
    from src.generate_topdown_layers import _collect_phase_files

    proj_dir = tempfile.mkdtemp()

    # The spec says: replace last "." with "-" unconditionally.
    # For ".hiddenfile", rfind('.') returns 0.
    # The bug (last_dot > 0 guard) skips replacement → dir_name stays ".hiddenfile"
    # Correct behavior: dir_name should be "-hiddenfile"

    # Create ONLY the spec-correct directory: extracted_functions/-hiddenfile
    correct_dir = os.path.join(proj_dir, "extracted_functions", "-hiddenfile")
    os.makedirs(correct_dir)
    with open(os.path.join(correct_dir, "some_func.py"), "w") as f:
        f.write("# extracted function content\n")

    phase_data = {
        "modules": [
            {
                "name": "test_module",
                "source_files": [".hiddenfile"]
            }
        ]
    }

    actual = _collect_phase_files(proj_dir, phase_data)

    # Expected (spec-correct): files from extracted_functions/-hiddenfile/ should be collected
    # Actual (buggy):     looks in extracted_functions/.hiddenfile/ instead → finds nothing
    expected_count = 1  # one file in -hiddenfile/
    actual_count = len(actual)

    passed = actual_count != expected_count  # True → bug reproduced (returned empty)

    if passed:
        print(f'CONFIRMED — actual count: {actual_count} | expected count: {expected_count}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual_count} file(s)')

    shutil.rmtree(proj_dir)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual count: 0 | expected count: 1
```
