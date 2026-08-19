# Bug Report: _funcs_from_commit

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_changed_functions::_funcs_from_commit.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dictionary whose keys are function name strings extracted from the old_commit_id revision of the file at rel_path and whose values are the corresponding function source text strings. The dictionary is empty when the file at rel_path contains no functions extractable by the lang_key extractor. Any temporary file created on disk during extraction is deleted before the function returns, regardless of whether extraction succeeds or raises an exception. If the git show command fails (e.g., invalid commit, missing file), the subprocess error propagates to the caller after temporary-file cleanup.

---

### Actual Behavior

If the code block completes normally, it returns a dictionary where each key is a non-empty function name and each value is the corresponding non-empty source code, extracted by `extract_functions_from_file` from a temporary file containing the content of `rel_path` at git revision `old_commit_id`. The temporary file created (using `tempfile.NamedTemporaryFile` with suffix `ext`) is reliably deleted via `os.unlink` in the `finally` block, so no such file persists after the function returns. If any exception occurs (e.g., from `_git`, file I/O, or `extract_functions_from_file`), that exception is propagated, but the `finally` block still executes, deleting the temporary file if it was successfully created and its path assigned to `tmp_path`. Formally, for a normal return with no exception: let `c = _git('show', f'{old_commit_id}:{rel_path}')`; there exists a file at path `p` such that its content equals `c` and `p` ends with `'.' + ext`; after the return, `os.path.exists(p)` is False; and the returned value satisfies `returned = dict(extract_functions_from_file(p, lang_key))`. For an exceptional return: if the temporary file at path `p` was created before the exception, then after the `finally` block `os.path.exists(p)` is False, and the exception is reraised; otherwise, no temporary file was created.

---

## Code Evidence

Line 4:     with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
Line 5:         tmp.write(text)
Line 6:         tmp_path = tmp.name

---

## Trigger Condition

The specification requires that any temporary file created on disk during extraction is deleted before the function returns, regardless of whether extraction succeeds or raises an exception. In the code, if `tmp.write(text)` raises an exception (e.g., due to a full disk), the file is created but `tmp_path` is not assigned, so the `finally` block never executes, and the temporary file is left on disk.

---

## How to trigger the bug

The bug occurs when `tmp.write(text)` raises an exception (e.g., `OSError` due to a full disk). The `tempfile.NamedTemporaryFile` with `delete=False` creates the file on disk during `__enter__`, but the assignment `tmp_path = tmp.name` on line 6 only executes after `write()` succeeds. If `write()` raises, `tmp_path` remains undefined, the `with` block exits with the exception propagating upward, and the subsequent `try/finally` block is never entered. The temp file remains on disk indefinitely.

### Inputs

| Parameter | Value |
|-----------|-------|
| `rel_path` | `"mod.py"` |
| `lang_key` | `"python"` |
| `ext` | `"py"` |
| `text` (git show output) | `"def foo():\n    return 1\n\ndef bar():\n    return 2\n"` |

### Expected (spec-correct) Output

Temporary file is deleted before returning, regardless of whether `write()` raises.

### Actual (buggy) Output

Temporary file (e.g., `/tmp/tmpgdrp9xnz.py`) remains on disk after the function raises due to write failure.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile

# Replicate the exact pattern from _funcs_from_commit
text = "def foo(): return 42\n"
ext = "py"
tmp_path = None  # never assigned when write fails

try:
    with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
        raise OSError("No space left on device (simulated)")
        tmp_path = tmp.name  # NEVER REACHED
    try:
        pass
    finally:
        if tmp_path:
            os.unlink(tmp_path)
except OSError:
    # temp file at tmp.name still exists on disk
    print("LEAKED:", os.path.exists(tmp.name), tmp.name)
# actual (buggy) output: LEAKED: True /tmp/tmpXXXXXX.py
# expected (correct) output: temp file should have been deleted
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe: verify that _funcs_from_commit leaks a temp file when tmp.write()
raises before tmp_path is assigned.

This reproduces the exact control-flow pattern from
src/incremental_reasoner.py:_funcs_from_commit (lines 439-448).
"""

import os
import tempfile

# ---- Reproduce the BUGGY pattern (exact same structure as the code) ----
# Original code:
#   def _funcs_from_commit(rel_path, lang_key, ext):
#       text = ...  # some string
#       with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
#           tmp.write(text)              # <-- (A)
#           tmp_path = tmp.name          # <-- (B)
#       try:
#           return dict(extract_functions_from_file(tmp_path, lang_key))
#       finally:
#           os.unlink(tmp_path)          # <-- (C)
#
# Bug: if (A) raises, (B) is never reached, so tmp_path is undefined,
# and (C) never executes. The temp file leaks on disk.

text = "def foo(): return 42\n"
ext = "py"
tmp_path = None

error_caught = False
file_leaked = False
actual_path = None

try:
    with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
        # ---- SIMULATE WRITE FAILURE (step A raises before step B) ----
        raise OSError("No space left on device (simulated)")
        # In real scenario: tmp.write(text) raises OSError
        # tmp_path = tmp.name  -- NEVER REACHED

    # ---- This try/finally block is NEVER REACHED ----
    try:
        pass
    finally:
        if tmp_path:
            os.unlink(tmp_path)

except OSError:
    error_caught = True
    # tmp_path was never assigned. The NamedTemporaryFile with delete=False
    # has created a file on disk. tmp.name IS valid (the NamedTemporaryFile
    # object exists even after write fails), but the code's tmp_path variable
    # was never assigned to it.
    #
    # Verify: the file still exists on disk.
    actual_path = tmp.name
    file_leaked = os.path.exists(actual_path)

# Cleanup
if actual_path and os.path.exists(actual_path):
    try:
        os.unlink(actual_path)
    except OSError:
        pass

# ---- Verdict ----
if error_caught and file_leaked:
    print(
        f"CONFIRMED — write failure caused temp file leak."
        f" File {actual_path!r} still on disk after exception."
        f" tmp_path was never assigned so cleanup never ran."
    )
elif error_caught:
    print("NOT CONFIRMED — exception raised but no file leak detected")
else:
    print("NOT CONFIRMED — no exception was raised")
```

### Probe Output

```
CONFIRMED — write failure caused temp file leak. File '/tmp/tmpgdrp9xnz.py' still on disk after exception. tmp_path was never assigned so cleanup never ran.
```
