# Bug Report: State::tail_events

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/State::tail_events.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If self.events_path does not exist as a file, returns immediately with no side effects. Otherwise: reads all bytes appended to the file since self._events_offset. If file size is strictly less than self._events_offset (indicating truncation or rotation), reading begins from byte 0. Every non-empty line that parses as valid JSON is appended to the State's in-memory event list; empty lines and lines that fail to parse as JSON are skipped. The order of appended events matches the line order in the file. self._events_offset is updated to the current end-of-file byte position.

---

### Actual Behavior

After a normal return from tail_events:
- If self.events_path does not exist, self._events_offset is unchanged and no events are ingested.
- Otherwise, let S_initial = initial self._events_offset, S_current = file size at entry. If S_initial > S_current (file truncated/rotated), self._events_offset is set to 0 before reading. Then if the offset equals the file size, the function returns immediately with no ingestion. Otherwise, it reads all remaining lines from that offset to end-of-file (as determined during the open-read block). Each non-empty line that successfully parses as a JSON object is passed to _ingest_event, which appends it to the in-memory event list in the order read. After the loop, self._events_offset is updated to f.tell() (the file position at end of file). Thus on normal return, self._events_offset equals the final file size, and the event list has been extended by exactly the sequence of valid, non-empty JSON objects found from the (possibly reset) offset to end-of-file. No other state is modified.
If an exception occurs during execution, the call does not return normally. In that case, self._events_offset may have been modified to 0 if the file was detected as truncated/rotated before the exception, and a prefix of the valid JSON lines (those processed before the exception) may have been ingested, but self._events_offset is not updated to f.tell(). The exact state is the result of executing a prefix of the normal execution path up to the point of the exception.

Formal logic (normal termination):
Let events be the in-memory event list before the call, off = self._events_offset.
After normal return: events' and off' denote post-state.
(exists(self.events_path)  
  let size = file_size(self.events_path) in
    (if off > size then off_reset = 0 else off_reset = off) 
    (if off_reset = size then off' = off  events' = events)
    else  lines = lines_from(off_reset, end) such that
      events' = events ++ [ pars...

---

## Code Evidence

Line 2:         if not self.events_path.exists():

---

## Trigger Condition

The specification states: 'If self.events_path does not exist as a file, returns immediately with no side effects.' When events_path is a directory, it does not exist 'as a file', yet Path.exists() returns True, so the early return is skipped. Execution proceeds to open() which raises IsADirectoryError, causing an abnormal exit instead of the required normal return with no side effects.

---

## How to trigger the bug

The bug occurs when `self.events_path` points to a directory rather than a regular file. `pathlib.Path.exists()` returns `True` for directories, so the early-return guard on line 234 of `dashboard.py` does not trigger. Execution falls through to `self.events_path.stat().st_size` and then `open(self.events_path, "r", ...)` which raises `IsADirectoryError`. The specification requires a normal return with no side effects when `events_path` is not a file.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A path whose `trace/` subdirectory contains a directory named `events.jsonl` instead of a file |

### Expected (spec-correct) Output

`tail_events()` returns normally with no side effects (no events ingested, `_events_offset` unchanged).

### Actual (buggy) Output

`tail_events()` raises `IsADirectoryError` because `open()` is called on a directory.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from dashboard import State

with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir_path = Path(tmpdir)
    trace_dir = tmpdir_path / "trace"
    trace_dir.mkdir()
    (trace_dir / "opencode").mkdir()
    
    # Create a directory named "events.jsonl" (not a regular file)
    (trace_dir / "events.jsonl").mkdir()
    
    state = State(str(tmpdir_path))
    state.tail_events()  # raises IsADirectoryError
    # actual (buggy) output: IsADirectoryError: [Errno 21] Is a directory: '.../events.jsonl'
    # expected (correct) output: normal return, no side effects
```

---

## Probe Script

```python
"""Probe for dashboard-py--State::tail_events bug: Path.exists() on a directory
does not trigger early return, leading to IsADirectoryError instead of the required
normal return with no side effects."""

import sys
import tempfile
import os
from pathlib import Path

# Add repo root to path so we can import dashboard
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import State
except Exception as e:
    print(f"ERROR: Failed to import dashboard.State: {e}")
    sys.exit(1)

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a trace directory inside tmpdir
        trace_dir = tmpdir_path / "trace"
        trace_dir.mkdir()

        # Create a directory named "events.jsonl" (not a file)
        # This simulates the bug trigger: events_path is a directory
        fake_events_path = trace_dir / "events.jsonl"
        fake_events_path.mkdir()

        # Also create opencode dir (required by State init)
        opencode_dir = trace_dir / "opencode"
        opencode_dir.mkdir()

        # Create State with proj_dir = tmpdir_path
        # This sets workdir = tmpdir_path (since tmpdir_path/trace exists)
        # and events_path = trace_dir / "events.jsonl" = fake_events_path (a directory)
        state = State(str(tmpdir_path))

        # Verify the events_path is indeed a directory
        if not state.events_path.is_dir():
            print(f"NOT CONFIRMED — events_path is not a directory: {state.events_path}")
        else:
            # Attempt tail_events() — the buggy code should raise IsADirectoryError
            # because Path.exists() returns True for directories
            try:
                state.tail_events()
                # If we get here without an exception, the code handled it somehow
                # But the spec says should return with no side effects, so check if
                # anything was modified (though for a directory, there's nothing to read)
                print("NOT CONFIRMED — tail_events() returned normally instead of raising an exception")
            except IsADirectoryError:
                print(f"CONFIRMED — tail_events() raised IsADirectoryError when events_path is a directory; "
                      f"spec requires normal return with no side effects")
            except OSError as e:
                if "Is a directory" in str(e) or "directory" in str(e).lower():
                    print(f"CONFIRMED — tail_events() raised OSError ({type(e).__name__}: {e}) "
                          f"when events_path is a directory; spec requires normal return with no side effects")
                else:
                    print(f"ERROR: Unexpected OSError: {e}")
                    sys.exit(1)
            except Exception as e:
                print(f"ERROR: {e}")
                sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — tail_events() raised IsADirectoryError when events_path is a directory; spec requires normal return with no side effects
```
