# Bug Report: _get_phase_files

**Source file:** `fm_agent/extracted_functions/src/file_utils-py/_get_phase_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of file identifiers (relative paths from input_dir) for all extracted function files belonging to the specified phase. Each identifier is a relative path to a regular file that is not a metadata sidecar file. No file identifier appears more than once in the returned list. Files within each extracted directory are returned in lexicographically ascending order of their names. Source files whose derived extracted directory does not exist on disk are skipped without raising an error.

---

### Actual Behavior

If the pre-condition holds and phases_data is well-formed, the function returns a list of relative file paths (relative to input_dir) of regular non-metadata files found within extracted directories corresponding to source files of the chosen phase. For each module in the phase and each source file in the module, build extracted_dir = os.path.join(input_dir, os.path.dirname(src_file), subdir) where subdir is the base name with the last dot replaced by '-' if present, else unchanged. If that directory exists, recursively walk it via os.walk, collecting paths of regular files (excluding those where _is_metadata_sidecar returns True) in alphabetical filename order; append their relative paths to the result. The order preserves module/source-file iteration and, within each directory, alphabetical filenames. Violations of structural assumptions (missing keys, non-iterable values, wrong types) result in a KeyError, TypeError, AttributeError, or StopIteration. The returned list may contain duplicate relative paths if the same file is encountered in multiple directories. Formal logic: R = concatenation_{m in modules} concatenation_{s in m['source_files']} [ os.path.relpath(os.path.join(root, fname), input_dir) for (root, _, fnames) in sorted(os.walk(extracted_dir(s))) for fname in sorted(fnames) if os.path.isfile(os.path.join(root, fname)) and not _is_metadata_sidecar(fname) ] where extracted_dir(s) is defined as above.

---

## Code Evidence

Line 24: phase_files.append(os.path.relpath(fpath, input_dir))

---

## Trigger Condition

The code never removes duplicates. If the same extracted directory is visited multiple times (e.g., because source_files contains duplicate entries), the same relative path is appended multiple times. The specification forbids any duplicate file identifiers.

---

## How to trigger the bug

The function iterates through modules and their source_files, building extracted directories for each source file. When source_files contains a duplicate entry (e.g., `["foo.py", "foo.py"]`), the same extracted directory (`input_dir/foo-py/`) is walked multiple times. Each walk appends the same relative path to the result list. The function never deduplicates the list before returning it.

### Inputs

| Parameter | Value |
|-----------|-------|
| phases_data | `{"phases": [{"phase": 1, "modules": [{"source_files": ["foo.py", "foo.py"]}]}]}` |
| phase_num | `1` |
| input_dir | temp directory containing `foo-py/some_func.py` |

### Expected (spec-correct) Output

`['foo-py/some_func.py']` — each file identifier appears exactly once, in sorted order.

### Actual (buggy) Output

`['foo-py/some_func.py', 'foo-py/some_func.py']` — the same relative path appears twice because the extracted directory was visited twice.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, shutil
from src.file_utils import _get_phase_files

tmpdir = tempfile.mkdtemp()
input_dir = os.path.join(tmpdir, 'extracted')
os.makedirs(input_dir)
extracted_dir = os.path.join(input_dir, 'foo-py')
os.makedirs(extracted_dir)
with open(os.path.join(extracted_dir, 'some_func.py'), 'w') as f:
    f.write('def some_func(): pass')

phases_data = {"phases": [{"phase": 1, "modules": [{"source_files": ["foo.py", "foo.py"]}]}]}
result = _get_phase_files(phases_data, 1, input_dir)

print(result)
# actual (buggy) output: ['foo-py/some_func.py', 'foo-py/some_func.py']
# expected (correct) output: ['foo-py/some_func.py']

shutil.rmtree(tmpdir)
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

try:
    from src.file_utils import _get_phase_files, _is_metadata_sidecar
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary input_dir that mimics extracted function structure
tmpdir = tempfile.mkdtemp(prefix='probe_get_phase_files_')
input_dir = os.path.join(tmpdir, 'extracted')
os.makedirs(input_dir)

# Create an extracted directory "foo-py" with one extracted function file inside
extracted_dir = os.path.join(input_dir, 'foo-py')
os.makedirs(extracted_dir)
func_file = os.path.join(extracted_dir, 'some_func.py')
with open(func_file, 'w') as f:
    f.write('def some_func(): pass')

# Also create a metadata sidecar that should be excluded
meta_file = os.path.join(extracted_dir, 'some_func.py.spec.json')
with open(meta_file, 'w') as f:
    f.write('{}')

# Build phases_data where source_files contains a duplicate entry for "foo.py"
phases_data = {
    "phases": [
        {
            "phase": 1,
            "modules": [
                {
                    "source_files": ["foo.py", "foo.py"]  # duplicate!
                }
            ]
        }
    ]
}

try:
    result = _get_phase_files(phases_data, 1, input_dir)
except Exception as e:
    print(f'ERROR: _get_phase_files raised: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(tmpdir)

# Check that metadata sidecar files are excluded
for path in result:
    if _is_metadata_sidecar(path):
        print(f'ERROR: metadata sidecar file found in result: {path}')
        sys.exit(1)

# Spec claim: "No file identifier appears more than once in the returned list."
# Bug claim: duplicates occur when source_files has duplicate entries
has_duplicates = len(result) != len(set(result))
unique_count = len(set(result))
total_count = len(result)

if has_duplicates:
    print(f'CONFIRMED — actual: {result!r} | expected: non-duplicate list of length 1')
    print(f'  total entries={total_count}, unique={unique_count}, duplicates={total_count - unique_count}')
else:
    print(f'NOT CONFIRMED — no duplicates found (length={total_count}, unique={unique_count})')
```

### Probe Output

```
CONFIRMED — actual: ['foo-py/some_func.py', 'foo-py/some_func.py'] | expected: non-duplicate list of length 1
  total entries=2, unique=1, duplicates=1
```
