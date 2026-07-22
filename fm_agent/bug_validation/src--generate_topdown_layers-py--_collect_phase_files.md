# Bug Report: _collect_phase_files

**Source file:** `src/generate_topdown_layers.py`
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

The function returns a list `results` such that:

results = [(file_path, module_name) for each module in phase_data.get('modules', []) if 'source_files' in module for each src_file in module['source_files'] where os.path.isdir(func_dir) for each regular file (os.path.isfile) with path file_path found by recursively walking func_dir via os.walk].

Here func_dir = os.path.join(proj_dir, 'extracted_functions', src_dir, dir_name) if src_dir (os.path.dirname(src_file)) is non-empty, else os.path.join(proj_dir, 'extracted_functions', dir_name). dir_name is derived from os.path.basename(src_file): if a last dot position > 0 exists, dir_name = basename[:last_dot] + '-' + basename[last_dot+1:]; otherwise dir_name = basename.

file_path is the absolute path (given proj_dir) of each file inside the extracted directory tree; module_name is the string module['name']. The order in results matches iteration order of modules, then source_files, and for each directory the order of files from os.walk (depth-first, top-down). The function has no side effects and raises no exceptions under the pre-condition.

---

## Code Evidence

Line 13: last_dot = src_base.rfind(".")
Line 14: if last_dot > 0:
Line 15: dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
Line 17: dir_name = src_base

---

## Trigger Condition

When a source file's basename starts with a dot (e.g., '.hidden'), the last dot is at index 0, and the condition last_dot > 0 fails, causing dir_name to remain '.hidden'. The specification replaces the last '.' with '-', which would produce '-hidden'. This leads the code to look for a directory '.hidden' instead of the expected '-hidden', missing files that should have been included.

---

## How to trigger the bug

The bug arises when a source file's basename begins with a dot (e.g., `.hidden`, `.envrc`, `.gitignore`). The `rfind(".")` call returns 0 for these names, and the guard `if last_dot > 0:` is False, so `dir_name` stays as the original basename (e.g., `.hidden`). Per the specification, the last `.` should be replaced with `-`, yielding `-hidden`. The function then looks for a directory named `.hidden` under `extracted_functions/` instead of the correct `-hidden`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary directory containing `extracted_functions/` |
| `phase_data` | `{"modules": [{"name": "test_module", "source_files": [".hidden"]}]}` |
| source file basename | `.hidden` (starts with a dot) |

### Expected (spec-correct) Output

`[("<tmp>/extracted_functions/-hidden/correct_file.py", "test_module")]`

### Actual (buggy) Output

`[("<tmp>/extracted_functions/.hidden/buggy_file.py", "test_module")]`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.generate_topdown_layers import _collect_phase_files

tmpdir = tempfile.mkdtemp()
extracted = os.path.join(tmpdir, "extracted_functions")

# Create both possible lookup directories
os.makedirs(os.path.join(extracted, "-hidden"))
with open(os.path.join(extracted, "-hidden", "correct.py"), "w") as f:
    f.write("# spec correct")

os.makedirs(os.path.join(extracted, ".hidden"))
with open(os.path.join(extracted, ".hidden", "buggy.py"), "w") as f:
    f.write("# buggy")

phase_data = {"modules": [{"name": "test_module", "source_files": [".hidden"]}]}
result = _collect_phase_files(tmpdir, phase_data)
print(result)
# actual (buggy) output: [(<path>/extracted_functions/.hidden/buggy.py, 'test_module')]
# expected (correct) output: [(<path>/extracted_functions/-hidden/correct.py, 'test_module')]
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Add repo root to path so `src` is importable
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _repo_root)

try:
    from src.generate_topdown_layers import _collect_phase_files
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create temp workspace — all fixtures isolated from the repo
tmpdir = tempfile.mkdtemp(prefix="probe_collect_phase_files_")
extracted_base = os.path.join(tmpdir, "extracted_functions")

# Directory the spec says should be looked up: -hidden
# (basename ".hidden" → replace last "." with "-" → "-hidden")
spec_correct_dir = os.path.join(extracted_base, "-hidden")
os.makedirs(spec_correct_dir, exist_ok=True)
with open(os.path.join(spec_correct_dir, "correct_file.py"), "w") as f:
    f.write("# spec correct\n")

# Directory the buggy code actually looks up: .hidden
# (last_dot == 0, last_dot > 0 is False, dir_name stays ".hidden")
buggy_dir = os.path.join(extracted_base, ".hidden")
os.makedirs(buggy_dir, exist_ok=True)
with open(os.path.join(buggy_dir, "buggy_file.py"), "w") as f:
    f.write("# buggy\n")

# phase_data with a source file whose basename starts with a "." (dot file)
phase_data = {
    "modules": [
        {
            "name": "test_module",
            "source_files": [".hidden"]
        }
    ]
}

results = _collect_phase_files(tmpdir, phase_data)
actual_files = {os.path.normpath(fp) for fp, _ in results}

spec_expected = {os.path.normpath(os.path.join(spec_correct_dir, "correct_file.py"))}
buggy_expected = {os.path.normpath(os.path.join(buggy_dir, "buggy_file.py"))}

# Cleanup before reporting
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)

if actual_files == spec_expected:
    print(f'NOT CONFIRMED — actual matched spec-expected: {actual_files}')
elif actual_files == buggy_expected:
    print(f'CONFIRMED — actual: {actual_files} | spec-expected (look in -hidden/): {spec_expected} | code looked in .hidden/ instead because last_dot>0 is False when last_dot==0')
elif not actual_files:
    print(f'NOT CONFIRMED — no files found (maybe neither directory was checked or dirs were cleaned)')
else:
    print(f'ERROR: unexpected result: actual={actual_files}, spec_expected={spec_expected}, buggy_expected={buggy_expected}')
```

### Probe Output

```
CONFIRMED — actual: {'/tmp/probe_collect_phase_files_cztzyoif/extracted_functions/.hidden/buggy_file.py'} | spec-expected (look in -hidden/): {'/tmp/probe_collect_phase_files_cztzyoif/extracted_functions/-hidden/correct_file.py'} | code looked in .hidden/ instead because last_dot>0 is False when last_dot==0
```
