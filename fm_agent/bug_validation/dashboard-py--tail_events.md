# Bug Report: State.tail_events

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Every non-blank line in self.events_path that was written after the
    byte position recorded in self._events_offset at call time is parsed
    as a JSON object and passed to self._ingest_event.
  - Lines that are blank or cannot be parsed as valid JSON are silently
    skipped and do not prevent processing of subsequent lines.
  - self._events_offset is updated to the file's end byte position after
    all newly written lines have been read.
  - If self.events_path does not exist, the function returns immediately
    and no state is modified.
  - If the file's current byte size is smaller than self._events_offset
    (indicating truncation or rotation), self._events_offset is reset to
    0 before reading, causing the entire file to be reprocessed.
  - If the file's current byte size equals self._events_offset (no new
    data written since the last call), the function returns immediately
    and no state is modified.

---

### Actual Behavior

Natural language post-condition:
If the method exits normally (no uncaught exception):
- If `self.events_path` does not exist, `self._events_offset` is unchanged.
- Otherwise, let `old_offset` be the value of `self._events_offset` before the call and `sz` be `self.events_path.stat().st_size` at the start of the call.
  - If `sz < old_offset`, then `self._events_offset` is set to 0.
  - If `sz == old_offset`, then `self._events_offset` remains `old_offset`.
  - If `sz > old_offset`, the method reads all lines from byte `old_offset` to the current end of file. For each line that is non-blank and parses successfully as JSON, `self._ingest_event` is called with the parsed object; blank lines or lines causing a JSON parse error are silently skipped. After processing every accessible line (i.e., when the file object reaches EOF), `self._events_offset` becomes the byte position returned by `f.tell()`, which is the file size at the moment reading completed (the new end-of-file).
If an exception is raised during the method (e.g., from file I/O operations or from `self._ingest_event`), `self._events_offset` remains unchanged. Any calls to `self._ingest_event` successfully performed before the exception remain in effect and cannot be rolled back.

---

## Code Evidence

Line 15-19: the try/except block only catches exceptions from json.loads, not from self._ingest_event; if _ingest_event raises, the method exits without updating offset and without processing the second line.

---

## Trigger Condition

The specification requires that every non-blank valid JSON line written after the byte position be passed to _ingest_event and then the offset be updated to the end of file. If _ingest_event raises an exception, the code exits prematurely, leaving offset unchanged and failing to process subsequent lines. This violates the guarantee that all lines are processed and that the offset is advanced past them.

---

## How to trigger the bug

When `self._ingest_event(ev)` raises an exception for a valid JSON line, the exception propagates out of the `with open(...)` block, skipping `self._events_offset = f.tell()`. This leaves `self._events_offset` unchanged (stuck at the previous value) and all subsequent valid JSON lines in the file unprocessed.

### Inputs

| Parameter | Value |
|-----------|-------|
| events.jsonl content | 3 valid JSON lines: `{"type": "first", "n": 1}`, `{"type": "second", "n": 2}`, `{"type": "third", "n": 3}` |
| self._events_offset before call | 0 |
| fail trigger | `_ingest_event` raises RuntimeError on the 2nd line |

### Expected (spec-correct) Output

All 3 lines ingested, `self._events_offset` updated to 79 (file size).

### Actual (buggy) Output

Only 2 lines ingested (3rd line skipped), `self._events_offset` remains at 0.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from dashboard import State

class BugState(State):
    def __init__(self, proj_dir):
        super().__init__(proj_dir)
        self.count = 0
        self.ingested = []
    def _ingest_event(self, ev):
        self.count += 1
        self.ingested.append(ev)
        if self.count == 2:
            raise RuntimeError("boom")

# Set up: project dir with trace/events.jsonl containing 3 valid JSON lines
import tempfile, json
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p / "trace").mkdir()
    with open(p / "trace" / "events.jsonl", "w") as f:
        for i in range(1, 4):
            f.write(json.dumps({"n": i}) + "\n")
    s = BugState(str(p))
    try:
        s.tail_events()
    except RuntimeError:
        pass
    # BUG: s._events_offset == 0 (should be file size)
    # BUG: len(s.ingested) == 2 (should be 3)
    # actual (buggy) output: offset=0, ingested=2
    # expected (correct) output: offset=file_size, ingested=3
```

---

## Probe Script

```python
"""Probe script for dashboard-py--tail_events bug.

Bug: In State.tail_events(), the try/except only wraps json.loads(), so
if self._ingest_event(ev) raises, the exception propagates, the for-loop
exits prematurely, self._events_offset is NOT updated, and subsequent
JSONL lines are never processed — violating the spec guarantee that every
valid line must be ingested and the offset advanced to end-of-file.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add repo root so we can import dashboard as a public module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import State


class BugProbeState(State):
    """Subclass that simulates an _ingest_event failure on a chosen line."""

    def __init__(self, proj_dir: str, fail_on_line: int = 1):
        super().__init__(proj_dir)
        self._line_count = 0
        self._fail_on_line = fail_on_line
        self._ingested_events = []

    def _ingest_event(self, ev):
        self._line_count += 1
        self._ingested_events.append(ev)
        if self._line_count == self._fail_on_line:
            raise RuntimeError(f"SIMULATED_FAILURE on line {self._line_count}")


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = Path(tmpdir)
        trace_dir = proj_dir / "trace"
        trace_dir.mkdir(parents=True)
        events_path = trace_dir / "events.jsonl"

        # Write 3 valid JSON lines (line 2 will trigger the simulated failure)
        events = [
            {"type": "first", "n": 1},
            {"type": "second", "n": 2},
            {"type": "third", "n": 3},
        ]
        with open(events_path, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        file_size = events_path.stat().st_size

        # Create state with _ingest_event set to fail on line 2
        state = BugProbeState(str(proj_dir), fail_on_line=2)

        try:
            state.tail_events()
        except RuntimeError:
            pass  # Expected — _ingest_event raised

        actual_ingested = len(state._ingested_events)
        actual_offset = state._events_offset

        # Bug IS confirmed if:
        #   (a) not all lines were ingested (should be 3), AND
        #   (b) _events_offset was not advanced to file size
        bug_present = (actual_ingested != 3) and (actual_offset != file_size)

        if bug_present:
            print(
                f"CONFIRMED — _ingest_event failure on line 2 caused early exit. "
                f"ingested={actual_ingested}/3, offset={actual_offset} (expected {file_size})"
            )
        else:
            print(
                f"NOT CONFIRMED — all {actual_ingested} lines ingested, "
                f"offset={actual_offset} (expected {file_size})"
            )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — _ingest_event failure on line 2 caused early exit. ingested=2/3, offset=0 (expected 79)
```
