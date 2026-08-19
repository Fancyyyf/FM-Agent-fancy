# Bug Report: _save_ignored

**Source file:** `src/env_check-py/_save_ignored.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Persists every check_id in ignored to the ignored-checks file under work_dir, one check_id per line. Creates the file if it does not exist; truncates and overwrites any previous content if it does. When ignored is an empty set, the file is created or truncated to empty. The function does not signal errors to the caller for any failure condition.

---

### Actual Behavior

After successful execution, the function creates or overwrites the file at path = _memory_path(work_dir). The file is closed, and its contents are the lines formed by each element of the input set `ignored` sorted in ascending order, each followed by a newline character, with no additional characters. Formally: let path = _memory_path(work_dir); then file_exists(path)   line  (readlines(path))  line = x + "\n" for some x  sorted(ignored)  length(readlines(path)) = |ignored|  closed(file_descriptor). If `ignored` is empty, the file is empty. The set `ignored` and the directory `work_dir` remain unchanged.

---

## Code Evidence

Line 3: with open(path, "w") as f:

---

## Trigger Condition

The code lacks exception handling; any I/O failure (e.g., permission denied) will raise an exception that propagates to the caller, signaling an error, while the specification requires that no errors are signaled to the caller for any failure condition.

---

## How to trigger the bug

The function `_save_ignored(work_dir, ignored)` constructs a file path via `_memory_path(work_dir)` and opens it for writing without any `try`/`except` block. When `work_dir` is a path whose parent exists but the directory itself does not, the `open()` call raises `FileNotFoundError`, which propagates to the caller.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A non-existent directory path (e.g. `/tmp/abc/nonexistent`) |
| `ignored` | `{"check1", "check2"}` |

### Expected (spec-correct) Output

No exception propagates — the function silently handles the I/O failure (e.g. by returning `None` or catching the exception internally).

### Actual (buggy) Output

`FileNotFoundError: [Errno 2] No such file or directory: '<work_dir>/.env_check_memory'` propagates to the caller.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile
sys.path.insert(0, ".")

from src.env_check import _save_ignored

with tempfile.TemporaryDirectory() as tmp:
    nonexistent_dir = os.path.join(tmp, "nonexistent")
    _save_ignored(nonexistent_dir, {"check1", "check2"})
    # actual (buggy) output: FileNotFoundError raised and propagated
    # expected (correct) output: no exception, silent handling
```

---

## Probe Script

```python
"""Probe for bug src--env_check-py--_save_ignored:
_save_ignored does not handle I/O errors, violating the spec that says
'the function does not signal errors to the caller for any failure condition.'
"""
import sys
import tempfile
import os

# The project uses [tool.uv] package = false — add repo root to path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.env_check import _save_ignored

    # Create a temp directory; use a nonexistent subdir as work_dir so that
    # open(path, "w") raises FileNotFoundError because the parent does not exist.
    with tempfile.TemporaryDirectory() as tmp:
        nonexistent_dir = os.path.join(tmp, "nonexistent")
        # This call should raise FileNotFoundError (or OSError) which propagates
        # to the caller, thus signaling an error — violating the spec.
        _save_ignored(nonexistent_dir, {"check1", "check2"})
        # If we reach here, no exception was raised.
        print("NOT CONFIRMED — _save_ignored silently handled a non-existent directory")
except FileNotFoundError as e:
    print(f"CONFIRMED — _save_ignored propagated FileNotFoundError: {e}")
except OSError as e:
    print(f"CONFIRMED — _save_ignored propagated OSError: {e}")
except Exception as e:
    print(f"ERROR: unexpected exception: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _save_ignored propagated FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmpyp3o7war/nonexistent/.env_check_memory'
```
