# Bug Report: _get_phase_files

**Source file:** `src/file_utils-py/_get_phase_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of relative path strings, each being the path from input_dir to a
    regular file located under an extracted-function subdirectory.
  - Each returned path originates from a source file declared in the modules of the
    phase identified by phase_num; the mapping from a source file path to its
    extracted-function subdirectory follows the engine convention: the last "." in the
    source file's basename is replaced by "-", and the resulting name is used as a
    subdirectory under input_dir joined with the source file's directory portion.
  - Source files whose corresponding extracted-function subdirectory does not exist
    under input_dir contribute no entries to the result (they are silently skipped).
  - Within each extracted-function subdirectory, contained regular files appear in
    lexicographically sorted order by filename.
  - The overall order of paths in the result preserves: the iteration order of
    phases_data["phases"], the iteration order of modules within the matched phase,
    and the iteration order of source_files within each module.
  - The returned list may be empty when the matched phase has no modules, no source
    files, or none of its source files have an existing extracted-function directory.

---

### Actual Behavior

If a phase dict with `phase == phase_num` exists, the function returns a list of relative file paths (strings) from `input_dir` for all regular files found inside the extracted directories that exist. Otherwise, `StopIteration` is raised; other exceptions (e.g., `OSError`) may propagate if filesystem operations fail. Formally:

 p  phases_data["phases"] : p["phase"] = phase_num 
  let M = {p | p  phases_data["phases"]  p["phase"] = phase_num} (singleton by pre-condition).
  For each module  M["modules"], for each src_file  module["source_files"]:
    let base = basename(src_file), ext_idx = base.rfind("."),
        subdir = (base[:ext_idx] + "-" + base[ext_idx+1:]) if ext_idx  0 else base,
        extracted_dir = join(input_dir, dirname(src_file), subdir).
    If is_dir(extracted_dir), then for every (root, dirs, files) in os.walk(extracted_dir) (top-down, arbitrary order),
    for every fname  sorted(files):
      let fpath = join(root, fname).
      If is_file(fpath), then append relpath(fpath, input_dir) to result list.
  Return the final list (deterministic for a given filesystem state).

Otherwise (no matching phase), `StopIteration` is raised.

---

## Code Evidence

Line 20: for root, _dirs, fnames in os.walk(extracted_dir):
Line 21: for fname in sorted(fnames):
Line 22: fpath = os.path.join(root, fname)
Line 23: if os.path.isfile(fpath):
Line 24: phase_files.append(os.path.relpath(fpath, input_dir))

---

## Trigger Condition

Specification requires that all regular files contained within an extracted-function subdirectory appear sorted by filename. The code uses os.walk and sorts files per-directory, so when subdirectories exist the overall list is not globally sorted. In the counterexample, the code returns ['dir/file-cpp/z.txt', 'dir/file-cpp/sub/a.txt'] but the specification demands ['dir/file-cpp/sub/a.txt', 'dir/file-cpp/z.txt'].

---

## How to trigger the bug

When an extracted-function subdirectory (e.g., `src/file-cpp/`) contains both root-level files and a nested subdirectory with files, `os.walk` traverses top-down — root-level files are yielded before child-directory files. Since sorting is per-directory, the overall result is not globally sorted by filename, violating the spec requirement.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_data` | `{"phases": [{"phase": 1, "modules": [{"source_files": ["src/file.cpp"]}]}]}` |
| `phase_num` | `1` |
| `input_dir` | path to directory containing `src/file-cpp/z.txt` and `src/file-cpp/sub/a.txt` |

### Expected (spec-correct) Output

`["src/file-cpp/sub/a.txt", "src/file-cpp/z.txt"]` — all regular files sorted by filename globally (a.txt < z.txt)

### Actual (buggy) Output

`["src/file-cpp/z.txt", "src/file-cpp/sub/a.txt"]` — os.walk top-down order (root first, then subdirectory)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1.  Navigate to the repo root.
2.  Create a directory structure:
    ```
    /tmp/test/input_dir/src/file-cpp/
        z.txt
        sub/
            a.txt
    ```
3.  Run the following snippet (uses the package entry point):

```python
import os, sys
sys.path.insert(0, "/path/to/repo")
from src.file_utils import _get_phase_files

phases_data = {
    "phases": [
        {"phase": 1, "modules": [{"source_files": ["src/file.cpp"]}]}
    ]
}
result = _get_phase_files(phases_data, 1, "/tmp/test/input_dir")
print(result)
# actual (buggy) output: ['src/file-cpp/z.txt', 'src/file-cpp/sub/a.txt']
# expected (correct) output: ['src/file-cpp/sub/a.txt', 'src/file-cpp/z.txt']
```

---

## Probe Script

```python
"""Probe script for _get_phase_files bug: os.walk order vs spec-required sort order."""
import sys
import os
import json
import tempfile

# ---------- create a reproducible trigger scenario ----------
#
# The spec says: "Within each extracted-function subdirectory, contained
# regular files appear in lexicographically sorted order by filename."
# When a subdirectory exists under the extracted-function directory, os.walk
# visits files in the parent before files in the child (top-down).  This
# violates the global-sort requirement.
#
# Trigger: create an extracted-dir that contains both a root-level file
# ("z.txt") and a child-directory file ("sub/a.txt").  The spec demands
# [".../sub/a.txt", ".../z.txt"] (alphabetical by filename), but os.walk
# returns [".../z.txt", ".../sub/a.txt"].
# ----------------------------------------------------------------

# Project root – needed so that `import src` resolves this project
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJ_ROOT)

try:
    from src.file_utils import _get_phase_files
except ImportError as e:
    print(f"ERROR: cannot import _get_phase_files: {e}")
    sys.exit(1)

# Build the fixture inside a fresh temporary directory (self-contained).
tmp_dir = tempfile.mkdtemp(prefix="probe_get_phase_files_")

try:
    input_dir = os.path.join(tmp_dir, "input_dir")
    os.makedirs(input_dir)

    # extracted-function subdirectory: src/file-cpp (file.cpp → file-cpp convention)
    extract_subdir = os.path.join(input_dir, "src", "file-cpp")
    child_dir = os.path.join(extract_subdir, "sub")
    os.makedirs(child_dir)

    # Root-level file inside extracted_dir (lexicographically "z.txt" > "a.txt")
    root_z = os.path.join(extract_subdir, "z.txt")
    with open(root_z, "w") as f:
        f.write("z")

    # Nested file inside sub/ (lexicographically "a.txt" < "z.txt")
    child_a = os.path.join(child_dir, "a.txt")
    with open(child_a, "w") as f:
        f.write("a")

    phases_data = {
        "phases": [
            {
                "phase": 1,
                "modules": [
                    {
                        "source_files": ["src/file.cpp"]
                    }
                ]
            }
        ]
    }

    actual = _get_phase_files(phases_data, 1, input_dir)

    # Expected (spec-correct): all regular files sorted by filename globally
    expected = sorted(actual, key=lambda p: os.path.basename(p))

    passed = actual != expected  # True → bug reproduced

    if passed:
        print(
            f"CONFIRMED — actual (os.walk order): {actual!r} | "
            f"expected (spec order): {expected!r}"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

finally:
    # Clean up the temporary fixture
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual (os.walk order): ['src/file-cpp/z.txt', 'src/file-cpp/sub/a.txt'] | expected (spec order): ['src/file-cpp/sub/a.txt', 'src/file-cpp/z.txt']
```
