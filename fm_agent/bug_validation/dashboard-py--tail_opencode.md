# Bug Report: tail_opencode

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/tail_opencode.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If self.opencode_dir does not exist, returns immediately with no side effects.
- All files ending in ".jsonl" in self.opencode_dir are visited in ascending
  lexicographic order of filename.
- For each such file: any content appended since the previous call to
  tail_opencode is consumed; if no previous offset was recorded for the file,
  all content is consumed.
- If a file has fewer bytes than its previously recorded offset (indicating
  truncation or rotation), the offset is silently reset to zero before reading.
- If a file has no new content since the last recorded offset, it is skipped.
- Every non-empty line in the new content that decodes as a valid JSON object
  is ingested by the State; lines that fail JSON decoding are silently skipped.
- After processing all files, the byte position immediately after the last
  consumed byte in each file is recorded so that a subsequent call to
  tail_opencode only reads content appended after that point.
- The State's aggregated metrics derived from OpenCode trace data are updated
  to reflect all newly ingested records.

---

### Actual Behavior

Natural language: If self.opencode_dir does not exist, the method returns immediately and the State is unchanged. Otherwise, it processes each JSONL file in the directory in alphabetical order. For each file, if os.stat fails (OSError), the file is skipped entirely with no change to its offset. If the files size is less than the stored offset, the offset is reset to 0. If after any reset the size equals the offset, the file is skipped and no records are ingested. Otherwise, the file is opened at the determined offset, every non-empty line is attempted to be parsed as JSON; successful parses are passed to self._ingest_opencode, which updates the States aggregated metrics, while lines that fail parsing are ignored. After processing all lines, the offset for that file is updated to the current file pointer position (f.tell()), which marks the end of the consumed content. If an exception occurs during opening any file, it propagates upward and the method terminates; in that case all files processed before the exception have their offsets updated and records ingested, while the failing file and subsequent files remain unmodified. After successful completion, all files that could be stat'd and had new content have been fully ingested, and for all such files the stored offset equals the file pointer at the end of the last read line. Files that were skipped or for which stat failed retain their prior offsets. The method is idempotent when re-run immediately: unless external changes occur, no work will be done because offsets will match file sizes.

---

## Code Evidence

Line 15: with open(path, "r", encoding="utf-8") as f:

---

## Trigger Condition

The specification (B) mandates that for every .jsonl file in the directory, any new content is consumed. The code does not handle exceptions from open(); when a file cannot be opened, the exception propagates and the method stops, leaving that file's content unconsumed and disregarding subsequent files. This directly violates the 'all files visited, content consumed' requirement.

---

## How to trigger the bug

The bug occurs when `open()` fails on a `.jsonl` file (e.g., due to permission errors or the file being deleted between `stat()` and `open()`). Unlike `os.stat()` failures which are caught and skipped via `except OSError: continue`, the `open()` call on line 354 (in the actual dashboard.py) is not wrapped in a try/except block. When `open()` fails, the exception propagates unchecked, terminating `tail_opencode()` immediately and leaving all subsequent `.jsonl` files in the directory unprocessed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `State.opencode_dir` | A directory containing at least two `.jsonl` files, where the first file in lexicographic order is unreadable (mode 000) |

### Expected (spec-correct) Output

`tail_opencode()` should skip the unreadable file gracefully and continue processing the remaining `.jsonl` files. All other files in the directory are visited and their content ingested.

### Actual (buggy) Output

`PermissionError` propagates from `open()`, crashing `tail_opencode()`. The unreadable file and all subsequent files are left unprocessed. No records are ingested.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import json
import tempfile
from pathlib import Path
from dashboard import State

tmpdir = Path(tempfile.mkdtemp())
opencode_dir = tmpdir / "opencode"
opencode_dir.mkdir(parents=True, exist_ok=True)

# Create two files: first unreadable, second with valid data
file_a = opencode_dir / "a.jsonl"
file_b = opencode_dir / "b.jsonl"
with open(file_a, "w") as f: f.write('{"test":1}\n')
with open(file_b, "w") as f: f.write('{"test":2}\n')
os.chmod(str(file_a), 0o000)

state = State(str(tmpdir))
state.opencode_dir = opencode_dir
state._opencode_offsets = {}
state.tail_opencode()  # PermissionError propagates here
# actual (buggy) output: PermissionError: [Errno 13] Permission denied: '.../a.jsonl'
# expected (correct) output: a.jsonl skipped silently; b.jsonl content ingested
```

---

## Probe Script

```python
"""Probe script: tail_opencode exception propagation on open() failure."""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

exception_raised = False
exception_msg = ""
records_ingested = 0

try:
    from dashboard import State
except Exception as e:
    print(f'ERROR: Failed to import dashboard: {e}')
    sys.exit(1)

# Setup: create a temp directory with .jsonl files
tmpdir = Path(tempfile.mkdtemp())
opencode_dir = tmpdir / "opencode"
opencode_dir.mkdir(parents=True, exist_ok=True)

# Create two .jsonl files in ascending lexicographic order
# a_first.jsonl — will be made unreadable
# b_second.jsonl — contains valid data that should be ingested per spec
file_a = opencode_dir / "a_first.jsonl"
file_b = opencode_dir / "b_second.jsonl"

# Write valid JSONL content to both files
valid_line = json.dumps({
    "_kind": "request",
    "_id": "test-req-1",
    "model": "test-model",
    "_ts": "2026-01-01T00:00:00Z"
}) + "\n"

with open(file_a, "w") as f:
    f.write(valid_line)

with open(file_b, "w") as f:
    f.write(valid_line)

# Make a_first.jsonl unreadable to trigger open() failure
os.chmod(str(file_a), 0o000)

# Create a State instance and override opencode_dir to point at our temp dir
state = State(str(tmpdir))
state.opencode_dir = opencode_dir
state._opencode_offsets = {}

actual_requests_before = len(state._opencode_requests)

try:
    state.tail_opencode()
except PermissionError as e:
    exception_raised = True
    exception_msg = str(e)
except OSError as e:
    exception_raised = True
    exception_msg = str(e)
except Exception as e:
    exception_raised = True
    exception_msg = str(e)

actual_requests_after = len(state._opencode_requests)
records_ingested = actual_requests_after - actual_requests_before

# Determine verdict:
# The spec says ALL files must be processed.
# If an exception propagated from open(), the bug is CONFIRMED because:
#   1. The method crashed instead of skipping the problematic file
#   2. Subsequent files (b_second.jsonl) were never processed
if exception_raised and records_ingested == 0:
    actual = 'exception propagated; subsequent files unprocessed'
    expected = 'exception caught/skipped; all remaining files processed'
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    print(f'  exception: {exception_msg}')
    print(f'  records ingested: {records_ingested}')
elif exception_raised and records_ingested > 0:
    actual = f'exception propagated; {records_ingested} records ingested before crash'
    expected = 'exception caught/skipped; all remaining files processed'
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    print(f'  exception: {exception_msg}')
    print(f'  records ingested: {records_ingested}')
else:
    actual = 'no exception raised; file skipped gracefully'
    expected = 'exception propagated (spec says all files must be processed)'
    print(f'NOT CONFIRMED — actual: {actual!r}')

# Cleanup
try:
    os.chmod(str(file_a), 0o644)
except Exception:
    pass
try:
    shutil.rmtree(str(tmpdir))
except Exception:
    pass

sys.exit(0)
```

### Probe Output

```
CONFIRMED — actual: 'exception propagated; subsequent files unprocessed' | expected: 'exception caught/skipped; all remaining files processed'
  exception: [Errno 13] Permission denied: '/tmp/tmp089yjpj8/opencode/a_first.jsonl'
  records ingested: 0
```
