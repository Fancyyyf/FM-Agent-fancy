# Bug Report: _extracted_files_by_method

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_extracted_files_by_method.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict whose keys are function identifier strings and whose values are non-empty lists of absolute file path strings. When func_dir exists as a directory: for every extracted function file found in a recursive traversal of func_dir (excluding metadata sidecar files), the file's absolute path is registered under its full file-stem identifier  the filename without its extension, which may contain '::' class-qualifier separators; additionally, when a stem contains '::', the substring after the last '::' (the bare method tail) is registered as an additional key mapping to the same path list. A single bare method tail maps to all paths from different classes that share that tail. When func_dir does not exist or is not a directory: returns an empty dict.

---

### Actual Behavior

The function returns a collections.defaultdict instance `index`, whose default factory is `list`. If an exception (e.g., FileNotFoundError, PermissionError) is raised during the call to `os.path.isdir(func_dir)` or during `os.walk(func_dir)`, the function propagates that exception and no return occurs. If execution completes normally: If `os.path.isdir(func_dir)` is False, then `index` is empty (i.e., for all keys k, `index[k] == []`). Otherwise, let `D` be the set of absolute paths of all regular files under the directory tree rooted at `func_dir` (recursively) whose basename `fn` satisfies `_is_metadata_sidecar(fn) == False`. Let `stem(f)` for a file `f` in `D` be defined as: `fn[:fn.rfind('.')]` if `'.'` is in the basename `fn` of `f`, else `fn`. Let `bare(f) = stem(f).split('::')[-1]`. Then `index` satisfies: for every key `k`, `index[k]` is a list containing exactly the absolute paths `f` in `D` such that `k == stem(f)` or (`k == bare(f)` and `bare(f) != stem(f)`). No other keys exist. The relative order of elements in each `index[k]` matches the order files are encountered by `os.walk` (depth-first, top-down). If `func_dir` is a directory but `D` is empty, all `index` values are empty lists.

---

## Code Evidence

Line 14: for root, _dirs, fnames in os.walk(func_dir):

---

## Trigger Condition

Specification requires returning a dict when func_dir exists as a directory. However, os.walk('/root') raises PermissionError for an unprivileged user, which the code propagates. This violates the specification because a dict is never returned.

---

## How to trigger the bug

When `func_dir` is a directory that exists (`os.path.isdir` returns True) but `os.walk` raises a `PermissionError` (e.g. traversing `/root` as an unprivileged user), the exception propagates unhandled from `_extracted_files_by_method`. The specification claims the function returns a dict in all cases; instead, no value is returned and calling code receives an unhandled exception.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func_dir` | Any existing directory where `os.walk` raises `PermissionError` (e.g. `/root` when run as non-root by an agent that patches `os.walk`, or any insufficiently-permissioned directory) |

### Expected (spec-correct) Output

`{}` (an empty dict, or a dict with the files that could be read)

### Actual (buggy) Output

`PermissionError` propagates; no dict returned

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from unittest.mock import patch
from src.incremental_reasoner import _extracted_files_by_method

# When os.walk raises PermissionError, the exception propagates instead of
# returning a dict as the spec requires.
with patch("os.walk", side_effect=PermissionError("Permission denied")):
    result = _extracted_files_by_method("/tmp")
    # Never reached — PermissionError is raised
```

---

## Probe Script

```py
import os
import sys
from unittest.mock import patch

# Add repo root to sys.path so that config.py and the src package are importable.
# The script lives at fm_agent/bug_validation/probe_<id>.py; the repo root is 3 levels up.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)

from src.incremental_reasoner import _extracted_files_by_method

# Simulate os.walk raising PermissionError, which mirrors the trigger
# condition "os.walk('/root') raises PermissionError for an unprivileged
# user". In this scenario the spec requires the function to return a dict,
# but the code propagates the exception unhandled.
try:
    with patch("os.walk", side_effect=PermissionError("Permission denied")):
        result = _extracted_files_by_method("/tmp")
        print(
            "NOT CONFIRMED — os.walk mock was bypassed or caught internally; "
            f"returned: {result!r} (type={type(result).__name__!r})"
        )
except PermissionError:
    print(
        "CONFIRMED — PermissionError from os.walk propagated "
        "instead of returning a dict"
    )
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — PermissionError from os.walk propagated instead of returning a dict
```
