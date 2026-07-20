# Bug Report: _payload_dir

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/src/opencode_trace-py/_payload_dir.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a filesystem path identifying a "payloads" subdirectory within trace_dir
  - After the call returns, the directory at the returned path exists on the filesystem
  - The directory is the designated storage location for trace event payload files
  - For a fixed trace_dir, every call to this function returns the same path

---

### Actual Behavior

If no exception is raised, the function returns the string obtained by joining trace_dir and 'payloads' (using os.path.join), and the directory at that path exists. The original trace_dir directory is not modified.

---

## Code Evidence

Line 3: os.makedirs(path, exist_ok=True)

---

## Trigger Condition

If a file named 'payloads' already exists at the target path, os.makedirs raises FileExistsError, so the function does not return a path and the directory does not exist, violating the specification's requirement that it returns a path and the directory exists after the call.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| trace_dir | <temp directory containing a file named "payloads"> |

### Expected (spec-correct) Output

A filesystem path to the "payloads" subdirectory (e.g., `<trace_dir>/payloads`), with the directory existing after the call returns.

### Actual (buggy) Output

`FileExistsError: [Errno 17] File exists: '<trace_dir>/payloads'` — the function raises an exception instead of returning a path, and no directory is created.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Create a temporary directory.
3. Create a file named `payloads` inside that directory (not a subdirectory).
4. Call `_payload_dir(trace_dir)` with that directory as `trace_dir`.
5. Observe `FileExistsError` raised.

```python
import os
import sys
import tempfile
sys.path.insert(0, os.getcwd())
from src import opencode_trace

trace_dir = tempfile.mkdtemp()
payloads_path = os.path.join(trace_dir, "payloads")
with open(payloads_path, "w") as f:
    f.write("blocking file")

# This raises FileExistsError because os.makedirs(path, exist_ok=True)
# only suppresses the error when the path is already a directory,
# NOT when it is a regular file.
result = opencode_trace._payload_dir(trace_dir)
# actual (buggy) output: FileExistsError: [Errno 17] File exists
# expected (correct) output: str path to the payloads directory

# Cleanup
os.remove(payloads_path)
os.rmdir(trace_dir)
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Add repo root to sys.path so 'src' and 'config' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src import opencode_trace

    # Create a temp directory to serve as trace_dir
    trace_dir = tempfile.mkdtemp(prefix="probe_payload_dir_")

    # Create a *file* named "payloads" inside trace_dir (not a directory)
    # This triggers the bug: os.makedirs(path, exist_ok=True) raises FileExistsError
    payloads_path = os.path.join(trace_dir, "payloads")
    with open(payloads_path, "w") as f:
        f.write("this is a file, not a directory")

    # Spec requires: returns a path, directory exists after call
    # Buggy behavior: FileExistsError raised because a file blocks directory creation
    expected = os.path.join(trace_dir, "payloads")
    passed = False
    actual = None
    error_msg = None

    try:
        actual = opencode_trace._payload_dir(trace_dir)
        # If we reached here, the function didn't raise - check if the returned path
        # exists as a directory. The spec says the directory at the returned path
        # exists on the filesystem after the call.
        passed = not os.path.isdir(actual)
    except FileExistsError as e:
        # This confirms the bug: the spec says the function returns a path and
        # directory exists, but instead FileExistsError is raised.
        error_msg = str(e)
        passed = True
    except Exception as e:
        error_msg = str(e)
        passed = False  # unexpected error

    # Cleanup
    os.remove(payloads_path)
    os.rmdir(trace_dir)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    if error_msg:
        print(f"CONFIRMED — FileExistsError raised: {error_msg!r}")
    else:
        print(f"CONFIRMED — actual: {actual!r} | expected directory, but not a dir")
else:
    print(f"NOT CONFIRMED — actual: {actual!r}")
```

### Probe Output

```
CONFIRMED — FileExistsError raised: "[Errno 17] File exists: '/tmp/probe_payload_dir_mwm4irs_/payloads'"
```
