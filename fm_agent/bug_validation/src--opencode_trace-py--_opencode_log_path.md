# Bug Report: _opencode_log_path

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a filesystem path under work_dir that is deterministically
    derived from work_dir and event_id alone
  - The returned path identifies the file where the subprocess stdout
    and stderr log output associated with event_id will be written
    during execution
  - For a fixed (work_dir, event_id) pair, every call to this function
    returns the same path

---

### Actual Behavior

The function returns a string that is the result of joining the path of the trace event payload subdirectory (obtained from _payload_dir(_trace_dir(work_dir))) with the filename f"{event_id}_opencode.log". The returned path string may not correspond to an existing file or directory. Formally: return_value = os.path.join(_payload_dir(_trace_dir(work_dir)), event_id + '_opencode.log').

---

## Code Evidence

Line 2: return os.path.join(_payload_dir(_trace_dir(work_dir)), f"{event_id}_opencode.log")

---

## Trigger Condition

If event_id begins with a slash (e.g., '/etc/passwd'), os.path.join ignores the first argument and returns an absolute path '/etc/passwd_opencode.log', which is not under work_dir as required by the specification.

---

## How to trigger the bug

The function `_opencode_log_path` constructs a log file path by joining the payload directory path with a filename derived from `event_id`. Python's `os.path.join` treats any component starting with `/` as an absolute path, discarding all preceding components. When `event_id` begins with `/`, the resulting path is absolute and rooted at `/` instead of under `work_dir`, directly violating the post-condition that the returned path must be under `work_dir`.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | `/tmp/tmps1e_18ww` (temp directory) |
| event_id | `/etc/passwd` |

### Expected (spec-correct) Output

A path under `work_dir`, e.g. `/tmp/tmps1e_18ww/trace/payloads/etc/passwd_opencode.log`

### Actual (buggy) Output

`/etc/passwd_opencode.log` — an absolute path outside `work_dir`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import _opencode_log_path
import tempfile

with tempfile.TemporaryDirectory() as work_dir:
    result = _opencode_log_path(work_dir, "/etc/passwd")
    # actual (buggy) output: '/etc/passwd_opencode.log'
    # expected (correct) output: a path under work_dir/trace/payloads/
    print(result)
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure the project root is on the path so we can import from src
_sys_path_adjust_count = 0
_proj_root = None
for _candidate in [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
]:
    _abs = os.path.abspath(_candidate)
    if os.path.isdir(os.path.join(_abs, "src")):
        _proj_root = _abs
        break
if _proj_root and _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)
    _sys_path_adjust_count += 1

try:
    from src.opencode_trace import _opencode_log_path
except ImportError as e:
    print(f"ERROR: cannot import _opencode_log_path: {e}")
    sys.exit(1)

try:
    with tempfile.TemporaryDirectory() as work_dir:
        event_id = "/etc/passwd"
        actual = _opencode_log_path(work_dir, event_id)

        work_dir_abs = os.path.abspath(work_dir)
        actual_abs = os.path.abspath(actual)

        # The spec requires the returned path to be under work_dir.
        # os.path.commonpath returns the longest common prefix;
        # if it equals work_dir_abs then actual is under work_dir.
        under_work_dir = (
            os.path.commonpath([actual_abs, work_dir_abs]) == work_dir_abs
        )

        if not under_work_dir:
            print(
                f"CONFIRMED — actual: {actual!r} is not under work_dir:"
                f" {work_dir_abs!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — actual: {actual!r} is under work_dir:"
                f" {work_dir_abs!r}"
            )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '/etc/passwd_opencode.log' is not under work_dir: '/tmp/tmps1e_18ww'
```
