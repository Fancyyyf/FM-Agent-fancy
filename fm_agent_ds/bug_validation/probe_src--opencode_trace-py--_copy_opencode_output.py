#!/usr/bin/env python3
"""Probe for _copy_opencode_output: TypeError when stream delivers bytes to a text-mode trace_log.

Spec claim: Every byte read from stream is written to the trace log file as UTF-8
encoded text with unencodable characters replaced.

Actual behavior: When the stream returns bytes (binary stream), line 10
(trace_log.write(chunk)) raises TypeError because the trace_log file is opened in
text mode and write() expects str, not bytes.
"""
import io
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.opencode_trace import _copy_opencode_output

    # Create a temporary directory for the trace log output
    tmp_dir = tempfile.mkdtemp(prefix="probe_copy_opencode_")
    trace_log_path = os.path.join(tmp_dir, "trace.log")

    # Create a binary stream containing data that will trigger the bug.
    # The byte b'\xff' is not valid UTF-8; per the spec it should be replaced
    # with the Unicode replacement character U+FFFD.
    binary_data = b"hello\xff\x00world"
    binary_stream = io.BytesIO(binary_data)

    type_error_raised = False
    actual_error = None

    try:
        _copy_opencode_output(binary_stream, trace_log_path)
    except TypeError as e:
        type_error_raised = True
        actual_error = str(e)
    except Exception as e:
        actual_error = f"{type(e).__name__}: {e}"
    else:
        # Function completed without error -- this would be NOT CONFIRMED
        pass

    # Verify the stream was closed (spec requires this)
    stream_was_closed = binary_stream.closed

    # The bug is confirmed if:
    # 1. TypeError was raised when trying to write bytes to a text file
    passed = type_error_raised

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — TypeError raised when writing bytes to text-mode trace log: "
        f"{actual_error}"
    )
else:
    if actual_error:
        print(f"NOT CONFIRMED — unexpected exception: {actual_error}")
    else:
        print("NOT CONFIRMED — function completed without error for binary stream")
