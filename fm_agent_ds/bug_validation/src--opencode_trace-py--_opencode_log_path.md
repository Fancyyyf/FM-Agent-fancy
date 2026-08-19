# Bug Report: _opencode_log_path

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/opencode_trace-py/_opencode_log_path.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

returns a filesystem path string within the trace directory structure derived from work_dir that uniquely identifies a log file for the given event_id; the returned path is derivable solely from work_dir and event_id and is suitable for writing subprocess stdout log content

---

### Actual Behavior

The function returns a string representing a file path. Let trace_dir = _trace_dir(work_dir) and payload_dir = _payload_dir(trace_dir). The return value ret satisfies: ret == os.path.join(payload_dir, f"{event_id}_opencode.log"). The returned string is a concatenation of the payload directory path and the filename composed of the event_id and the suffix '_opencode.log', using the OS-specific path separator.

---

## Code Evidence

Line 2: return os.path.join(_payload_dir(_trace_dir(work_dir)), f"{event_id}_opencode.log")

---

## Trigger Condition

The specification requires the returned path to be within the trace directory structure. With event_id='../../malicious', the returned path escapes the trace directory, violating the requirement.

---

## How to trigger the bug

The function `_opencode_log_path` uses `os.path.join()` to construct the output path without validating or sanitizing `event_id`. When `event_id` contains path traversal sequences such as `../../malicious`, the resolved absolute path escapes the `trace/` directory structure — the log file would be written to a location outside the intended trace directory.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | any writable directory path |
| `event_id` | `../../malicious` |

### Expected (spec-correct) Output

A path string strictly within `<work_dir>/trace/` — e.g. `<work_dir>/trace/payloads/<sanitized_event_id>_opencode.log`

### Actual (buggy) Output

Path escapes the trace directory — e.g. `<work_dir>/malicious_opencode.log` (the `../` sequences walk up from `trace/payloads/` into the parent of `trace/`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import _opencode_log_path

# actual (buggy) output: path outside <work_dir>/trace/
_ = _opencode_log_path("/tmp/my_run", "../../malicious")
# actual:  /tmp/my_run/malicious_opencode.log
# expected: /tmp/my_run/trace/payloads/<...>_opencode.log
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe: path traversal in _opencode_log_path via malicious event_id.

Bug: _opencode_log_path does not sanitize event_id, allowing path traversal
when event_id contains "../" sequences. The spec requires the returned path
to stay within the trace directory structure.

Public API: from src.opencode_trace import _opencode_log_path
"""

import os
import sys
import tempfile


def main():
    # Add repo root to path so that 'from src.opencode_trace import ...' works
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    try:
        from src.opencode_trace import _opencode_log_path  # type: ignore
    except ImportError as exc:
        print(f"ERROR: Cannot import _opencode_log_path: {exc}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = os.path.join(tmpdir, "run")
        os.makedirs(work_dir, exist_ok=True)

        # Establish the expected trace boundaries
        trace_dir = os.path.join(work_dir, "trace")
        payload_dir = os.path.join(trace_dir, "payloads")
        os.makedirs(payload_dir, exist_ok=True)

        # Call with a path-traversal event_id
        event_id = "../../malicious"
        try:
            actual_path = _opencode_log_path(work_dir, event_id)
        except Exception as exc:
            print(f"ERROR: _opencode_log_path raised: {exc}")
            sys.exit(1)

        # Resolve both to canonical absolute paths for comparison
        actual_abs = os.path.realpath(actual_path)
        # The spec says the path must stay within the trace directory structure
        trace_abs = os.path.realpath(trace_dir)

        # A correct path would be under trace_abs; a traversed path won't be
        within_trace = os.path.commonpath([actual_abs, trace_abs]) == trace_abs

        if not within_trace:
            print(
                f"CONFIRMED — path traversal successful\n"
                f"  work_dir:      {work_dir}\n"
                f"  trace_dir:     {trace_dir}\n"
                f"  expected_under: {trace_abs}\n"
                f"  actual_path:   {actual_abs}\n"
                f"  event_id:      {event_id!r}\n"
                f"  escaped trace directory"
            )
        else:
            print(f"NOT CONFIRMED — path remained within trace directory: {actual_abs}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — path traversal successful
  work_dir:      /tmp/tmpbeyck_mv/run
  trace_dir:     /tmp/tmpbeyck_mv/run/trace
  expected_under: /tmp/tmpbeyck_mv/run/trace
  actual_path:   /tmp/tmpbeyck_mv/run/malicious_opencode.log
  event_id:      '../../malicious'
  escaped trace directory
```
