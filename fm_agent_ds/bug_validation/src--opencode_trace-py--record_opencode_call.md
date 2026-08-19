# Bug Report: record_opencode_call

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Atomically appends one structured event record as a single JSON line to events.jsonl under the trace directory derived from work_dir. The persisted record is self-contained: it includes the event identifier, stage, status label, both start and end timestamps, the full command, the exit code, and all optional metadata fields exactly as supplied (omitted optional fields stored as their empty defaults). When a file exists at the provided opencode log path, a reference to that log is included in the record. When a file exists at the provided opencode trace path, a reference to that trace is included. Callers observe exactly one new, complete event record in events.jsonl per invocation.

---

### Actual Behavior

After successful completion, the function returns None. The trace directory `trace_dir = _trace_dir(work_dir)` is computed. If the optional `opencode_log_path` is provided and the file exists, a child entry of type 'tool_output', label 'opencode-stdout', with path and content_ref set to `_payload_ref(trace_dir, opencode_log_path)` is created; otherwise no such child is added. Similarly, if `opencode_trace_path` is provided and the file exists, a child entry of type 'tool_output', label 'opencode-llm-jsonl' with path and content_ref set to `_payload_ref(trace_dir, opencode_trace_path)` is created. An event record is then written via `record_trace_event(trace_dir, E)` where `E` is a dictionary containing: 'event_id' exactly equal to the input `event_id`, 'type' equal to 'opencode_call', 'stage' equal to input `stage`, 'status' equal to input `status` (either 'success' or 'error'), 'start_time' equal to input `started` (ISO 8601 UTC), 'end_time' equal to input `ended` (ISO 8601 UTC, not earlier than `started`), 'summary' equal to input `summary` if it is non-None, else the string `'OpenCode {stage}'` formatted with input `stage`, 'function_ids' equal to input `function_ids` if non-None, else `[]`, 'children' equal to the constructed list of children (as described), 'metadata' a dictionary containing: 'command' equal to `command_argv(command)` (the result of splitting `command` into an argument array), 'exit_code' equal to the input `exit_code` (integer or None), 'input_files' equal to input `input_files` if non-None else `[]`, 'output_files' equal to input `output_files` if non-None else `[]`, 'error' equal to input `error`, all key-value pairs from input `metadata` if non-None else `{}`, and 'command_display' equal to `command_display(command)`. The original input arguments remain unchanged.

---

## Code Evidence

```python
Line 289: "summary": summary or f"OpenCode {stage}",
```

---

## Trigger Condition

With summary=None (omitted), the code sets the record's summary to 'OpenCode build', whereas the specification requires that omitted optional fields be stored as their empty defaults (e.g., None or an empty string). This alters the supplied value and violates the exact-supplied-or-empty-default requirement.

---

## How to trigger the bug

When `record_opencode_call` is called with `summary=None`, the Python expression `summary or f"OpenCode {stage}"` evaluates to `f"OpenCode {stage}"` because `None` is falsy. The spec requires that omitted optional fields be stored as their empty defaults (i.e., `None`), but instead the function substitutes a generated string.

### Inputs

| Parameter | Value |
|-----------|-------|
| `summary` | `None` |
| `stage` | `"build"` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`"OpenCode build"`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import record_opencode_call
from unittest.mock import patch
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    captured = {}
    def capture(trace_dir, event):
        captured.update(event)

    with patch("src.opencode_trace.record_trace_event", side_effect=capture), \
         patch("os.path.exists", return_value=False):
        record_opencode_call(
            work_dir=tmpdir,
            event_id="test_evt_001",
            stage="build",
            status="success",
            started="2025-01-01T00:00:00Z",
            ended="2025-01-01T00:01:00Z",
            command="opencode run",
            summary=None,
        )
    print(captured.get("summary"))
# actual (buggy) output: "OpenCode build"
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe for record_opencode_call: summary=None should store None, not f"OpenCode {stage}"."""
import sys
import tempfile
import os
from unittest.mock import patch

try:
    # Load via package entry point — import the internal function from the package module
    from src.opencode_trace import record_opencode_call

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = tmpdir
        captured_event = {}

        def fake_record_trace_event(trace_dir, event):
            captured_event.update(event)

        with (
            patch("src.opencode_trace.record_trace_event", side_effect=fake_record_trace_event),
            patch("os.path.exists", return_value=False),
        ):
            record_opencode_call(
                work_dir=work_dir,
                event_id="test_evt_001",
                stage="build",
                status="success",
                started="2025-01-01T00:00:00Z",
                ended="2025-01-01T00:01:00Z",
                command="opencode run",
                summary=None,            # Omitted — spec says store empty default
                function_ids=None,
                input_files=None,
                output_files=None,
                exit_code=0,
                error=None,
                metadata=None,
                opencode_log_path=None,
                opencode_trace_path=None,
            )

        actual_summary = captured_event.get("summary")
        expected_summary = None       # spec: omitted optional → empty default

        passed = actual_summary != expected_summary

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual summary: {actual_summary!r} | expected: {expected_summary!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_summary!r}")
```

### Probe Output

```
CONFIRMED — actual summary: 'OpenCode build' | expected: None
```
