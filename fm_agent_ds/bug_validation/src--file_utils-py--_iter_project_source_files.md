# Bug Report: _iter_project_source_files

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/file_utils-py/_iter_project_source_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Yields (abs_path, rel_path) tuples for every source file under proj_dir that is not a test file, where abs_path is the absolute path and rel_path is the path relative to proj_dir using forward-slash separators. When submodules is not None, yields only files whose relative path begins with one of the submodule directory names. Files whose extension is not among the recognized source extensions are excluded. Files under hidden directories or non-source directories are excluded. Terminates after yielding all matching files; yields zero tuples when no files match.

---

### Actual Behavior

After the generator object returned by `_iter_project_source_files(proj_dir, submodules)` is iterated to exhaustion, exactly one of the following holds:
- If the module `src.extract` cannot be imported, an `ImportError` is raised during the first `next()` call (or equivalent) and no values are yielded.
- Otherwise, no exception is raised, and the multiset of yielded strings equals the multiset defined by:
  Let `EXT_TO_LANG` be the dictionary imported from `src.extract`.
  Let `root_dirs = [proj_dir]` if `submodules is None`, else `[os.path.join(proj_dir, s.replace('/', os.sep)) for s in submodules]`.
  Let `EXCLUDE_DIRS = {'node_modules', '__pycache__', 'venv', '.venv', 'fm_agent'}`.
  For a directory name `d`, define `rejected(d) = d.startswith('.') or d in EXCLUDE_DIRS`.
  For a file name `f`, define `valid_ext(f) = (ext = f.rsplit('.', 1)[-1] if '.' in f else '') in EXT_TO_LANG.keys()`.
  For a relative path `r` (with forward slashes), define `under_submod(r) = (submodules is None) or any(r.startswith(s) for s in submodules)`.
  For each scan root `sr` in `root_dirs`, define `F(sr) = { os.path.relpath(p, proj_dir).replace(os.sep, '/') | p is a regular file under `sr`, the relative directory path from `sr` to `p` contains no directory name `d` such that `rejected(d)`, `valid_ext(basename(p))` holds, and `under_submod` holds for the resulting relative path }`.
  The multiset of yielded strings is the multiset union `_{sr  root_dirs} F(sr)`. Yields occur in an order consistent with iterating over `root_dirs` and, for each `sr`, depthfirst traversal by `os.walk` (exact ordering is implementationdefined). Duplicates are preserved if a file belongs to multiple `F(sr)`. No external state is modified.

---

## Code Evidence

Line 20-23: yield rel

---

## Trigger Condition

The code yields only relative path strings, violating the specification that expects (abs_path, rel_path) tuples. Additionally, the specification requires excluding test files, but no test file filtering exists in the code.

---

## How to trigger the bug

The function `_iter_project_source_files` has two confirmed bugs:

1. **Yields strings instead of tuples**: The function yields bare relative-path strings (`yield rel` at line 244 of `src/file_utils.py`) rather than `(abs_path, rel_path)` tuples as required by the specification.

2. **No test file exclusion**: The function contains no call to `_is_test_file()` (defined in the same module at line 254). Test files with names matching patterns like `test_*.py` are yielded alongside regular source files, violating the specification requirement to exclude test files.

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | `/tmp/probe_iter_project_XXXXXX` (temporary directory) |
| `submodules` | `None` (default) |

### Expected (spec-correct) Output

Two `(abs_path, rel_path)` tuples for `main.py` only (test file excluded):
- `('/tmp/probe_iter_project_XXXXXX/main.py', 'main.py')`

### Actual (buggy) Output

Two bare strings for both `test_main.py` and `main.py` (test file included, no tuples):
- `'test_main.py'`
- `'main.py'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _iter_project_source_files
results = list(_iter_project_source_files('some/project/dir'))
for r in results:
    print(type(r), r)
# actual (buggy) output: <class 'str'> test_main.py
# actual (buggy) output: <class 'str'> main.py
# expected (correct) output: <class 'tuple'> ('/path/to/main.py', 'main.py')
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

try:
    from src.file_utils import _iter_project_source_files

    # Create a fresh temporary directory for the probe workspace
    tmpdir = tempfile.mkdtemp(prefix="probe_iter_project_")

    # Create a regular source file that should be included
    with open(os.path.join(tmpdir, 'main.py'), 'w') as f:
        f.write('print("hello")\n')

    # Create a test file (test_main.py) that should be excluded per spec
    with open(os.path.join(tmpdir, 'test_main.py'), 'w') as f:
        f.write('def test_foo():\n    pass\n')

    # Call _iter_project_source_files on the temp directory
    results = list(_iter_project_source_files(tmpdir))

    # --- Bug 1: Yields strings instead of (abs_path, rel_path) tuples ---
    bug1_confirmed = False
    bug1_detail = ''
    if results:
        first = results[0]
        if isinstance(first, str):
            bug1_confirmed = True
            bug1_detail = f'yielded {type(first).__name__} (value: {first!r}) — expected tuple'
        elif isinstance(first, tuple):
            bug1_detail = f'yielded tuple — matched spec'
        else:
            bug1_detail = f'yielded {type(first).__name__} — unexpected type'

    # --- Bug 2: test files not excluded ---
    # Resolved test file basenames with a test-file naming pattern
    test_file_names = [
        os.path.basename(r)
        for r in results
        if 'test' in os.path.basename(r).lower()
    ]
    bug2_confirmed = len(test_file_names) > 0
    bug2_detail = (
        f'{len(test_file_names)} test-pattern files found among {len(results)} results: {test_file_names}'
        if test_file_names
        else f'no test-pattern files among {len(results)} results'
    )

    # Cleanup
    shutil.rmtree(tmpdir)

    # Print verdict
    if bug1_confirmed or bug2_confirmed:
        print('CONFIRMED')
        if bug1_confirmed:
            print(f'  Bug 1 (yields string, not tuple): {bug1_detail}')
        if bug2_confirmed:
            print(f'  Bug 2 (test files not excluded): {bug2_detail}')
    else:
        print('NOT CONFIRMED')
        print(f'  Bug 1 detail: {bug1_detail}')
        print(f'  Bug 2 detail: {bug2_detail}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED
  Bug 1 (yields string, not tuple): yielded str (value: 'test_main.py') — expected tuple
  Bug 2 (test files not excluded): 1 test-pattern files found among 2 results: ['test_main.py']
```
