# Bug Report: _load_ignored

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/env_check-py/_load_ignored.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the set of non-empty check_id strings read from the ignored-checks file under work_dir, where each entry is stripped of leading and trailing whitespace and blank lines are discarded. Returns an empty set when the file does not exist, cannot be read, or yields zero non-empty entries after stripping. The function has no side effects — it does not create, modify, or delete the ignored-checks file or any other file or directory.

---

### Actual Behavior

If the file at path = _memory_path(work_dir) exists and can be opened for reading without raising IOError, then the function returns the set {line.strip() for line in file(path) if line.strip() != ''}. Otherwise, the function returns the empty set. The function has no side effects: work_dir and the file system are unmodified, and no exception propagates.

---

## Code Evidence

Line 7: except IOError:

---

## Trigger Condition

Specification B requires returning an empty set when the file cannot be read, which includes decoding errors. The code only catches IOError, so a UnicodeDecodeError (a subclass of ValueError, not OSError) will propagate, violating the post-condition that an empty set is returned.

---

## How to trigger the bug

The `_load_ignored` function opens the ignored-checks file in text mode (`open(path, "r")`) but only catches `IOError`. When the file contains bytes that are not valid UTF-8 (the default text encoding on Linux), `open()` raises a `UnicodeDecodeError` — which is a subclass of `ValueError`, not `IOError`/`OSError`. Because only `IOError` is caught (line 7), the `UnicodeDecodeError` propagates instead of the function returning an empty set as the spec requires.

### Inputs

| Parameter | Value |
|---|---|
| `work_dir` | Path to a temporary directory containing a `.env_check_memory` file with invalid UTF-8 bytes (`\xff\xfe`) |

### Expected (spec-correct) Output

`set()` (empty set)

### Actual (buggy) Output

`UnicodeDecodeError` propagates (unhandled exception)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, sys
sys.path.insert(0, os.getcwd())

from src.env_check import _load_ignored

tmp_dir = tempfile.mkdtemp()
file_path = os.path.join(tmp_dir, '.env_check_memory')

with open(file_path, 'wb') as f:
    f.write(b'\xff\xfe')

# This raises UnicodeDecodeError instead of returning set()
_load_ignored(tmp_dir)
# actual (buggy) output: UnicodeDecodeError propagates
# expected (correct) output: set()
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

# Add repo root to Python path so 'src' package is importable.
# The probe is executed from the repo root per the validator instructions.
sys.path.insert(0, os.getcwd())

try:
    from src.env_check import _load_ignored
except Exception as e:
    print(f'ERROR: Failed to import _load_ignored from src.env_check: {e}')
    sys.exit(1)

# Create a temporary directory with a .env_check_memory file containing
# invalid UTF-8 bytes (0xff is never valid UTF-8 by itself).
tmp_dir = tempfile.mkdtemp(prefix='bug_probe_')
file_path = os.path.join(tmp_dir, '.env_check_memory')

try:
    with open(file_path, 'wb') as f:
        f.write(b'\xff\xfe')

    # _load_ignored opens the file in text mode (default encoding),
    # which should raise UnicodeDecodeError on invalid UTF-8.
    actual = _load_ignored(tmp_dir)

    # If we reach here, no exception was raised — bug NOT confirmed.
    print(f'NOT CONFIRMED — _load_ignored returned {actual!r} without raising UnicodeDecodeError')
except UnicodeDecodeError:
    # The spec requires returning an empty set when the file "cannot be read."
    # UnicodeDecodeError is not caught by the except IOError handler,
    # so the exception propagates — bug CONFIRMED.
    print('CONFIRMED — UnicodeDecodeError propagated instead of returning empty set')
except Exception as e:
    print(f'ERROR: Unexpected exception: {type(e).__name__}: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — UnicodeDecodeError propagated instead of returning empty set
```
