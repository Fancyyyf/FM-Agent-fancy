# Bug Report: append_event

**Source file:** `src/trace_writer.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The directory trace_dir exists, with any missing parent directories created
  - The file events.jsonl inside trace_dir has one additional line appended
  - That line is the JSON serialization of event with non-ASCII characters preserved in their original form (Unicode, not \u-escaped)
  - The write is safe under concurrency: each event occupies exactly one complete line and bytes from different events are never interleaved within the same line
  - Returns None

---

### Actual Behavior

After execution, the lock _LOCK is released. If the block completes without raising an exception, then: (1) the directory trace_dir exists (and all missing parent directories exist); (2) the file events_path = os.path.join(trace_dir, 'events.jsonl') exists and its content is the previous content (if any) appended with the line json.dumps(event, ensure_ascii=False) + '\n'; (3) the function returns None. If an exception is raised, the directory may or may not exist depending on whether _ensure_trace_dirs succeeded, the file may be untouched, created but empty, or contain a partial write; the lock is released in all cases. Formally, let S be the initial state and S' the final state, let exists(p) denote path p exists, content(p) the file contents, and line = json.dumps(event, ensure_ascii=False). Then: (exception  (exists(trace_dir)  exists(events_path)  content(events_path) = content(events_path)_S  line  '\n'  ret = None))  (exception  (lock_released  (exists(trace_dir)  exists(trace_dir)))) where  denotes string concatenation.

---

## Code Evidence

Line 6: with open(events_path, "a", encoding="utf-8") as f:
Line 7: f.write(line + "\n")

---

## Trigger Condition

The code unconditionally appends the serialized event and a newline after the existing content. If the existing content does not end with a newline, the new event is concatenated to the last (incomplete) line, causing two events to occupy a single line. This violates the specification requirement that each event occupies exactly one complete line.

---

## How to trigger the bug

The `append_event` function opens `events.jsonl` in append mode (`"a"`) and writes `line + "\n"`. If the existing file content does not end with a newline character, the new event is concatenated directly to the last incomplete line rather than starting on its own line.

### Inputs

| Parameter | Value |
|-----------|-------|
| trace_dir | `/tmp/tmpXXXXXX` (a temporary directory) |
| event | `{"event": "new", "data": "test"}` |
| Pre-existing file content | `{"partial": ` (no trailing newline) |

### Expected (spec-correct) Output

The file `events.jsonl` should contain two separate lines:

```
{"partial": 
{"event": "new", "data": "test"}
```

### Actual (buggy) Output

The file `events.jsonl` contains a single line with both events concatenated:

```
{"partial": {"event": "new", "data": "test"}
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.trace_writer import append_event

tmpdir = tempfile.mkdtemp()
events_path = os.path.join(tmpdir, "events.jsonl")

# Write partial content without trailing newline
with open(events_path, "w", encoding="utf-8") as f:
    f.write('{"partial": ')

# Append a new event
append_event(tmpdir, {"event": "new", "data": "test"})

# Read back — result is a single concatenated line
with open(events_path, "r", encoding="utf-8") as f:
    print(repr(f.read()))
# actual (buggy) output: '{"partial": {"event": "new", "data": "test"}\n'
# expected (correct) output: '{"partial": \n{"event": "new", "data": "test"}\n'
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# Use the package entry point (src.trace_writer)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.trace_writer import append_event

tmpdir = None
try:
    tmpdir = tempfile.mkdtemp()
    events_path = os.path.join(tmpdir, "events.jsonl")

    # Trigger condition: write content that does NOT end with a newline
    with open(events_path, "w", encoding="utf-8") as f:
        f.write('{"partial": ')

    # Call append_event with a new event
    new_event = {"event": "new", "data": "test"}
    append_event(tmpdir, new_event)

    # Read back the file content
    with open(events_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify: spec says each event occupies exactly one complete line.
    # If bug exists, new event is concatenated onto the same line as the partial content.
    new_event_json = json.dumps(new_event, ensure_ascii=False)

    if '\n' + new_event_json in content:
        print(f'NOT CONFIRMED — new event is on its own line: {content!r}')
    else:
        print(f'CONFIRMED — new event concatenated to incomplete line: {content!r}')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
finally:
    if tmpdir and os.path.exists(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — new event concatenated to incomplete line: '{"partial": {"event": "new", "data": "test"}\n'
```
