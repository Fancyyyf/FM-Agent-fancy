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
