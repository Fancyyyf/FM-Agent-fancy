import sys
import os

# Add repo root to sys.path so 'src' is importable as the package entry point
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src import opencode_trace
except Exception as e:
    print(f'ERROR: failed to import src.opencode_trace: {e}')
    sys.exit(1)


class MockFlushFailStream:
    """A mock stream where write() succeeds but flush() raises RuntimeError."""

    def __init__(self):
        self.written = ""
        self.closed = False
        self.write_called = False
        self.flush_called = False

    def write(self, text):
        self.write_called = True
        self.written += text
        return len(text)

    def flush(self):
        self.flush_called = True
        raise RuntimeError("flush() failed — simulated I/O error")

    def close(self):
        self.closed = True


stream = MockFlushFailStream()
text = "hello stdin"
exception_raised = False
actual_exception = None
write_succeeded_before_exception = False
closed_after_exception = False

try:
    opencode_trace._write_command_stdin(stream, text)
except RuntimeError as exc:
    exception_raised = True
    actual_exception = exc
    write_succeeded_before_exception = stream.write_called
    closed_after_exception = stream.closed
except Exception as exc:
    exception_raised = True
    actual_exception = exc
    write_succeeded_before_exception = stream.write_called
    closed_after_exception = stream.closed

# The spec requires: text is written AND flushed
# Actual behavior: write() succeeded, flush() raised, exception propagates, stream is closed
# The gap: write() happened, but flush() raised — the spec's postcondition that
# "text has been flushed via flush()" is violated. The caller cannot observe the
# postcondition because the exception propagates unhandled.

bug_confirmed = (
    exception_raised
    and write_succeeded_before_exception
    and closed_after_exception
)

if bug_confirmed:
    print(
        "CONFIRMED — actual: RuntimeError raised after write(), flush() failed. "
        "Spec requires text written AND flushed, but flush() failure means the "
        "postcondition is violated. Stream was closed via finally block."
    )
else:
    print(
        "NOT CONFIRMED — "
        f"exception_raised={exception_raised}, "
        f"write_succeeded={write_succeeded_before_exception}, "
        f"flush_called_and_failed={stream.flush_called}, "
        f"closed={closed_after_exception}"
    )
