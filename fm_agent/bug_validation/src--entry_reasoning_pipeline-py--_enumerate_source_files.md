# Bug Report: _enumerate_source_files

**Source file:** `src/entry_reasoning_pipeline-py/_enumerate_source_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a sorted list (ascending lexicographic order) of source-file
    relative paths (using "/" separators) for every regular file under
    proj_dir that satisfies ALL of the following:
    a) Not located within any subdirectory named "fm_agent" or ".git" at any
       nesting level below proj_dir
    b) Has a file extension for which EXT_TO_LANG returns a truthy value
    c) _is_test_file returns False for the relative path
  - The returned paths are relative to proj_dir
  - The returned list is in ascending lexicographic order
  - Files excluded by test-file heuristics are omitted; the test-file
    exemption for the entry function is a caller-side concern and does not
    affect this function's output

---

### Actual Behavior

The function returns a sorted list of strings, each representing a relative path (using '/' separators) from proj_dir to a Python source file. The list includes every file that (a) resides under proj_dir after skipping the 'fm_agent' and '.git' directories during traversal, (b) has a file extension mapped by EXT_TO_LANG, and (c) is not classified as a test file by _is_test_file. No other files are included. The returned list is sorted in lexicographical order. The function has no side effects: proj_dir and the global EXT_TO_LANG are unmodified. Given the pre-condition that proj_dir exists, the walk completes without raising an exception. Formally: let F = { f_rel |  f_abs  Walk(proj_dir, skip={'fm_agent','.git'}) such that f_rel = relpath(f_abs, proj_dir).replace(os.sep,'/'), ext(f_rel)  keys(EXT_TO_LANG) and _is_test_file(f_rel) }. Then result = sorted(list(F)), where Walk yields all file paths after directory pruning.

---

## Code Evidence

Line 14: ext = fname.rsplit(".", 1)[-1] if "." in fname else ""
Line 15: if EXT_TO_LANG.get(ext) and not _is_test_file(src_rel):

---

## Trigger Condition

The specification condition (b) requires a file to have a file extension for which EXT_TO_LANG returns a truthy value. A file without a dot does not have any file extension. The code, however, maps such files to an empty string extension and includes them if EXT_TO_LANG[''] is truthy, violating the specification.

---

## How to trigger the bug

When a file without a dot in its name (e.g. `README`, `Makefile`) exists under `proj_dir` and the empty string `""` maps to a truthy value in `EXT_TO_LANG`, the function incorrectly includes that file in its result. The specification requires that only files with a recognized file extension be included; dotless files have no extension and should never match.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Temporary directory containing files: `README` (no extension), `real.py`, `subdir/Makefile` (no extension) |

### Expected (spec-correct) Output

`['real.py']`

### Actual (buggy) Output

`['README', 'real.py', 'subdir/Makefile']`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
import sys; sys.path.insert(0, '.')
from src.extract import EXT_TO_LANG
from src.entry_reasoning_pipeline import _enumerate_source_files

tmpdir = tempfile.mkdtemp()
os.makedirs(os.path.join(tmpdir, 'subdir'), exist_ok=True)
with open(os.path.join(tmpdir, 'README'), 'w'): pass
with open(os.path.join(tmpdir, 'real.py'), 'w'): pass
with open(os.path.join(tmpdir, 'subdir', 'Makefile'), 'w'): pass

EXT_TO_LANG[''] = 'noext'  # trigger the bug
result = _enumerate_source_files(tmpdir)
print(result)
# actual (buggy) output: ['README', 'real.py', 'subdir/Makefile']
# expected (correct) output: ['real.py']
```

---

## Probe Script

```python
"""Probe script for _enumerate_source_files bug.

Demonstrates that the function uses '' as fallback extension for dotless files
and would incorrectly include them if EXT_TO_LANG[''] were truthy, violating
the spec which requires files to have an actual file extension.
"""
import sys
import os
import tempfile
import shutil

# Script runs from repo root; ensure project is importable
sys.path.insert(0, os.getcwd())

tmpdir = None
try:
    from src.extract import EXT_TO_LANG
    from src.entry_reasoning_pipeline import _enumerate_source_files

    tmpdir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmpdir, 'subdir'), exist_ok=True)

    # Create files: one with no extension, one with a valid extension
    with open(os.path.join(tmpdir, 'README'), 'w') as f:
        f.write('test')
    with open(os.path.join(tmpdir, 'real.py'), 'w') as f:
        f.write('print(1)')
    with open(os.path.join(tmpdir, 'subdir', 'Makefile'), 'w') as f:
        f.write('test')

    # Monkey-patch EXT_TO_LANG so '' maps to a truthy value.
    # This simulates what would happen if someone added '' to EXT_TO_LANG.
    EXT_TO_LANG[''] = 'noext'

    result = _enumerate_source_files(tmpdir)

    # Per spec: only 'real.py' should be included (file has extension 'py'
    # which maps to truthy). README and Makefile have no extension and
    # should NOT be included.
    dotless_included = [f for f in result if '.' not in os.path.basename(f)]
    passed = len(dotless_included) > 0  # True -> bug reproduced

    if passed:
        print(
            f'CONFIRMED — dotless files included: {dotless_included!r} '
            f'| actual result: {result!r} | expected (spec): no dotless files'
        )
    else:
        print(f'NOT CONFIRMED — actual matched expected: {result!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    if 'EXT_TO_LANG' in dir():
        try:
            del EXT_TO_LANG['']
        except (KeyError, NameError):
            pass
    if tmpdir is not None:
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — dotless files included: ['README', 'subdir/Makefile'] | actual result: ['README', 'real.py', 'subdir/Makefile'] | expected (spec): no dotless files
```
