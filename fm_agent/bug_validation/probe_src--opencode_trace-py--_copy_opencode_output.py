"""Probe script: verify that stream.close() is skipped when exception occurs during read."""

import sys
import os
import importlib.util
import tempfile

# Load the extracted function module via importlib (no __init__.py in tree)
module_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "extracted_functions",
    "src",
    "opencode_trace-py",
    "_copy_opencode_output.py",
)
spec = importlib.util.spec_from_file_location("_copy_opencode_output", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_copy_opencode_output = mod._copy_opencode_output


class FaultyStream:
    """A readable stream that raises OSError after returning some data."""

    def __init__(self):
        self.closed = False

    def read(self, _n):
        raise OSError("simulated stream read error after some data")

    def close(self):
        self.closed = True


def run_test(desc, trace_log_path):
    stream = FaultyStream()
    exception_caught = False
    try:
        _copy_opencode_output(stream, trace_log_path=trace_log_path)
    except OSError:
        exception_caught = True
    except Exception as e:
        print(f"ERROR: unexpected exception type in {desc}: {type(e).__name__}: {e}")
        return False, False

    if not exception_caught:
        print(f"ERROR: expected OSError was not raised in {desc}")
        return False, False

    return exception_caught, stream.closed


# Test 1: trace_log_path=None (no file opened)
exception_raised_1, stream_closed_1 = run_test("no trace log", trace_log_path=None)

# Test 2: trace_log_path set (file opened, write happens or fails)
tmp_path = os.path.join(tempfile.gettempdir(), f"probe_test_{os.getpid()}.log")
exception_raised_2, stream_closed_2 = None, None
try:
    exception_raised_2, stream_closed_2 = run_test("with trace log", trace_log_path=tmp_path)
finally:
    # Clean up
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

# Both tests should show: exception raised but stream NOT closed (bug)
stream_leaked = (exception_raised_1 and not stream_closed_1)

if exception_raised_1 is None or exception_raised_2 is None:
    print("ERROR: tests did not complete")
    sys.exit(1)

if stream_leaked:
    print(
        "CONFIRMED — exception raised but stream.close() was NOT called "
        "(stayed open). The spec requires stream is guaranteed closed regardless "
        "of exceptions, but stream.close() is outside the finally block."
    )
else:
    print(
        "NOT CONFIRMED — stream was closed despite the exception, "
        "or the expected OSError was not raised."
    )
