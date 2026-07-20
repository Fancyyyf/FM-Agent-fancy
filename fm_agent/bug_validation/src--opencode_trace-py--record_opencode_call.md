# Bug Report: record_opencode_call

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Appends exactly one trace event of type "opencode_call" as a single JSON line to the
    trace events file under work_dir (specifically trace/events.jsonl within work_dir)
  - The recorded event's event_id, stage, status, start_time, end_time reflect the
    corresponding parameter values unchanged
  - The recorded event's function_ids is the provided list when non-None, or an empty list
    when None
  - The recorded event's summary is the provided value when non-None, or a default string
    of the form "OpenCode <stage>" when None
  - When opencode_log_path is provided and the file it refers to actually exists on disk,
    the event includes a child payload entry of type "tool_output" labeled "opencode-stdout",
    referencing the file via a path relative to the trace directory; when the file does not
    exist or opencode_log_path is None, no such child entry is included
  - When opencode_trace_path is provided and the file it refers to actually exists on disk,
    the event includes a child payload entry of type "tool_output" labeled "opencode-llm-jsonl",
    referencing the file via a path relative to the trace directory; when the file does not
    exist or opencode_trace_path is None, no such child entry is included
  - The event's metadata block merges: the full argv of command, exit_code, input_files
    (empty list when None), output_files (empty list when None), error, a display-formatted
    command string, and every key-value pair from the provided metadata dict (when not None)
  - Returns None — all effects are side effects on the trace events file

---

### Actual Behavior

The function returns None. It writes a trace event to the file `events.jsonl` inside the trace directory derived from `work_dir` (i.e., `_trace_dir(work_dir)`), creating parent directories and the file if they do not exist. The event is a JSON object `e` with the following properties: `e.event_id = event_id`; `e.type = 'opencode_call'`; `e.stage = stage`; `e.status = status`; `e.start_time = started`; `e.end_time = ended`; `e.summary = summary if summary is not None else 'OpenCode ' + stage`; `e.function_ids = function_ids if function_ids is not None else []`; `e.children` is a list built by including a child entry with type 'tool_output', label 'opencode-stdout', path and content_ref equal to the normalized relative path of `opencode_log_path` within the trace directory if `opencode_log_path` is not None and the file exists, and similarly for `opencode_trace_path` with label 'opencode-llm-jsonl'; `e.metadata` is a dictionary containing the keys `'command'` (set to `command_argv(command)`), `'exit_code'` (value `exit_code`), `'input_files'` (`input_files` or `[]`), `'output_files'` (`output_files` or `[]`), `'error'` (`error`), `'command_display'` (value `command_display(command)`), plus all key-value pairs from `metadata` if not None. Formally, after execution the trace file contains an additional line encoding the above object, and no exceptions are raised given the pre-conditions.

---

## Code Evidence

Line 48: "summary": summary or f"OpenCode {stage}"

---

## Trigger Condition

The code uses `summary or ...` which substitutes the default summary for any falsy value (e.g., empty string), while the specification requires using the provided summary for any non-None value. This causes incorrect output when the caller passes a non-None but falsy summary.

---

## How to trigger the bug

Passing an empty string as `summary` (a non-None but falsy value) causes the code to substitute the default summary `"OpenCode <stage>"` instead of preserving the empty string as required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | temporary directory |
| `event_id` | `"test_bug_001"` |
| `stage` | `"setup"` |
| `status` | `"success"` |
| `started` | `"2025-01-01T00:00:00Z"` |
| `ended` | `"2025-01-01T00:01:00Z"` |
| `command` | `["echo", "hello"]` |
| `summary` | `""` (empty string — non-None, falsy) |

### Expected (spec-correct) Output

`""` (empty string — the provided value used as-is per the specification)

### Actual (buggy) Output

`"OpenCode setup"` (the default substituted because empty string is falsy)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import record_opencode_call
import tempfile, os, json

with tempfile.TemporaryDirectory() as work_dir:
    record_opencode_call(
        work_dir=work_dir,
        event_id="test_bug_001",
        stage="setup",
        status="success",
        started="2025-01-01T00:00:00Z",
        ended="2025-01-01T00:01:00Z",
        command=["echo", "hello"],
        summary="",
    )
    events_path = os.path.join(work_dir, "trace", "events.jsonl")
    with open(events_path) as f:
        event = json.loads(f.readline())
    print(repr(event["summary"]))
    # actual (buggy) output: 'OpenCode setup'
    # expected (correct) output: ''
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile

# Add repo root to sys.path so we can import the package
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.opencode_trace import record_opencode_call

    # Bug: `summary or f"OpenCode {stage}"` treats any falsy value (like empty
    # string "") the same as None. The spec says only None should trigger the
    # default; an explicitly provided empty string should be used as-is.
    with tempfile.TemporaryDirectory() as work_dir:
        record_opencode_call(
            work_dir=work_dir,
            event_id="test_bug_001",
            stage="setup",
            status="success",
            started="2025-01-01T00:00:00Z",
            ended="2025-01-01T00:01:00Z",
            command=["echo", "hello"],
            summary="",  # non-None but falsy — spec says use it, code substitutes default
        )

        events_path = os.path.join(work_dir, "trace", "events.jsonl")
        with open(events_path, encoding="utf-8") as f:
            event = json.loads(f.readline().strip())

        actual = event["summary"]
        expected = ""  # spec: use provided value when non-None

        if actual != expected:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'OpenCode setup' | expected: ''
```
