# Bug Report: _iter_project_source_files

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Yields zero or more relative file paths using "/" as the path separator
  - Every yielded path is relative to proj_dir and identifies a regular file under
    proj_dir whose filename extension matches a pipeline-supported programming language
  - The traversal excludes directories whose names begin with "." and those whose
    names belong to a predefined set of well-known directories that contain generated
    artifacts, dependencies, or tool workspace output rather than project source code
  - When submodules is None, every qualifying file under the full proj_dir tree
    (subject to the directory exclusions above) is yielded
  - When submodules is provided and non-empty, only qualifying files whose
    project-relative path begins with one of the listed subdirectory name prefixes
    are yielded
  - The function does not create, modify, delete, or rename any file or directory

---

### Actual Behavior

The function `_iter_project_source_files(proj_dir, submodules)` returns a generator object. When the generator is iterated to exhaustion without exceptions, it yields a sequence of unique project-relative file paths (using '/' as the separator) that satisfy the following conditions. The set of yielded paths is exactly:

{ rel | 
  let scan_roots = {proj_dir} if submodules is None or empty, else { os.path.join(proj_dir, s.replace('/', os.sep)) for s in submodules };
  there exists a scan root sr in scan_roots such that:
    when walking sr with os.walk, directories whose name starts with '.' or whose name is in {'node_modules', '__pycache__', 'venv', '.venv', 'fm_agent'} are pruned (i.e., not recursed into);
    there exists a file path fp in the remaining tree such that:
      let ext = the substring after the last '.' in the filename, or '' if no dot; ext is a key of the dictionary EXT_TO_LANG (imported from src.extract);
      let rel_candidate = os.path.relpath(fp, proj_dir) with all os.sep replaced by '/';
      and _is_under_submodules(rel_candidate, submodules) returns True.
}

According to the post-condition of _is_under_submodules, if submodules is None this check always passes; otherwise, it requires rel_candidate to begin with one of the submodule strings (as a '/'separated prefix).

The generator yields no duplicates and does not modify any external state. If an exception occurs during iteration (e.g., ImportError when loading src.extract, OSError from filesystem operations, ValueError from relpath), it is raised to the caller and the generator stops; the sequence of previously yielded paths is a prefix of the full set.

---

## Code Evidence

Line 8: os.path.join(proj_dir, submodule.replace("/", os.sep)) - constructs a path without checking existence; Line 12: os.walk(scan_root) raises FileNotFoundError

---

## Trigger Condition

For submodules=['nonexistent'] the specification requires yielding only files whose project-relative path begins with 'nonexistent/'. Since no such files exist, the expected output is an empty sequence. The actual code attempts os.walk on the non-existent directory and raises an OSError, violating the yield-only specification.

---

## How to trigger the bug

The bug could **not** be reproduced on the required Python version (3.12.3). Three attempts were made with varied inputs.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot` |
| submodules | `['nonexistent']` (Attempt 1) |
| submodules | `['nonexistent/deep']`, `['nonexistent/', 'nonexistent2']`, `['../escape']` (Attempt 2) |
| submodules | Race condition: directory created then removed immediately (Attempt 3) |

### Expected (spec-correct) Output

`[]` (empty sequence — no files match the non-existent submodule prefix)

### Actual (buggy) Output

`[]` — In all three attempts, `_iter_project_source_files()` returned an empty list without raising any exception. Python 3.12's `os.walk()` silently handles non-existent directories by returning an empty generator, so the claimed `FileNotFoundError` does not occur.

### How to Reproduce

```python
import sys, os
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot')
import src.file_utils as fu

proj_dir = '/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot'
actual   = list(fu._iter_project_source_files(proj_dir, submodules=['nonexistent']))
expected = []
# actual (observed) output: [] (empty list, no exception)
# expected (correct) output: [] (empty list)
```

---

## Probe Script

```python
import sys, os

# Ensure repo root on sys.path for package imports
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot')

import src.file_utils as fu

proj_dir = '/tmp/fm_agent_wt_FM-Agent_ip161ped/snapshot'

# Trigger: submodules=['nonexistent']
# Spec claim: yields only files whose project-relative path begins with 'nonexistent/'.
# Since no such files exist, expected output is empty sequence [].
# Actual bug: os.walk raises FileNotFoundError on non-existent directory.

try:
    actual = list(fu._iter_project_source_files(proj_dir, submodules=['nonexistent']))
    expected = []
    # Bug reproduced if actual != expected (which shouldn't happen since it should crash)
    # But if no crash, check the output
    if actual != expected:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except FileNotFoundError as e:
    print(f'CONFIRMED — actual: FileNotFoundError raised ({e}) | expected: empty sequence []')
except OSError as e:
    # OSError is the parent of FileNotFoundError; catching it too for safety
    print(f'CONFIRMED — actual: OSError raised ({e}) | expected: empty sequence []')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: []
```
