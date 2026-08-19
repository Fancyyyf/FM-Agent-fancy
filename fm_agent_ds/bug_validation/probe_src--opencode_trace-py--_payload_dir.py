"""Probe script for bug `src--opencode_trace-py--_payload_dir`.

Tests whether `_payload_dir` handles the case where `trace_dir` points to a file
instead of a directory.  The specification requires the function to return a
path and ensure the directory exists on every call, but the implementation
lets `os.makedirs` propagate an OSError when the parent path is a file.
"""

import os
import shutil
import sys
import tempfile

# Load the package through its public entry point (repo root on sys.path).
_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')
)
sys.path.insert(0, _repo_root)
import src.opencode_trace

actual = None
expected = 'a valid path (dir exists)'
passed = False

# Create an isolated workspace so the probe does not touch any FM-Agent dirs.
workspace = tempfile.mkdtemp(prefix='probe__payload_dir_')

try:
    # Arrange: create a file where a directory is expected.
    file_as_trace_dir = os.path.join(workspace, 'not_a_dir')
    with open(file_as_trace_dir, 'w') as f:
        f.write('this is a file, not a directory')

    # Act: call _payload_dir with a file path (trigger_condition).
    result = src.opencode_trace._payload_dir(file_as_trace_dir)

    # If we reach here, no exception was raised — bug NOT confirmed.
    actual = repr(result)
    passed = False

except Exception as exc:
    actual = f'{type(exc).__name__}: {exc}'
    # The bug is confirmed if an OSError propagates unhandled.
    passed = isinstance(exc, OSError)

finally:
    shutil.rmtree(workspace, ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')
