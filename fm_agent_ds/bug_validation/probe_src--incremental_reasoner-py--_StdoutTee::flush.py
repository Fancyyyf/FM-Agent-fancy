"""Probe script for bug: _StdoutTee::flush — log stream not flushed when console flush raises."""

import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'config' and 'src' are both importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Create an isolated temp directory for any probe-owned file I/O
# (even though this test is pure in-memory, the guard requires it).
_probe_tmp = tempfile.mkdtemp(prefix="probe_StdoutTee_flush_")


# ---------------------------------------------------------------------------
# Mock objects
# ---------------------------------------------------------------------------
class RaisingConsole:
    """A console stream whose flush() deliberately raises IOError."""

    def write(self, data):
        pass

    def flush(self):
        raise IOError("Simulated console flush failure")


class TrackingLogStream:
    """A log stream that records whether flush() was called."""

    def __init__(self):
        self.closed = False
        self.flush_called = False

    def write(self, data):
        pass

    def flush(self):
        self.flush_called = True


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------
def main():
    try:
        from src.incremental_reasoner import _StdoutTee
    except ImportError as e:
        print(f"ERROR: Could not import _StdoutTee: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during import of _StdoutTee: {e}")
        sys.exit(1)

    console = RaisingConsole()
    log_stream = TrackingLogStream()
    tee = _StdoutTee(console, log_stream)

    # According to the spec, flush() must flush both the console stream and
    # the log stream (unless the log stream is closed). The bug report states
    # that when self._console.flush() raises, self._log_stream.flush() is
    # never reached, violating this post-condition.
    #
    # We trigger the bug by calling flush() on a tee backed by a
    # deliberately-failing console.
    exception_raised = False
    try:
        tee.flush()
    except IOError:
        exception_raised = True
    except Exception as e:
        print(f"ERROR: Unexpected exception type from flush(): {type(e).__name__}: {e}")
        sys.exit(1)

    # Classification:
    #
    # If an exception propagated AND the log stream was NOT flushed →
    # the bug is confirmed: the spec requires the log flush, but the code
    # never reaches it.
    #
    # If an exception propagated BUT the log stream WAS flushed →
    # the code was fixed to flush the log before/despite the console error.
    #
    # If no exception propagated (flush returned normally) →
    # the mock was not raising as expected (should not happen with IOError).
    if exception_raised and not log_stream.flush_called:
        print(
            "CONFIRMED — exception propagated from console flush, "
            "but log stream flush was never called (spec requires it)"
        )
    elif exception_raised and log_stream.flush_called:
        print(
            "NOT CONFIRMED — exception propagated, "
            "but log stream was flushed before the exception (spec satisfied)"
        )
    elif not exception_raised:
        # flush() returned normally: either the exception was swallowed
        # internally, or some other unexpected behavior occurred.
        if log_stream.flush_called:
            print(
                "NOT CONFIRMED — flush() returned normally and "
                "log stream was flushed (exception was handled gracefully)"
            )
        else:
            print(
                "NOT CONFIRMED — flush() returned normally but "
                "log stream was not flushed (unexpected behavior)"
            )


if __name__ == "__main__":
    main()
