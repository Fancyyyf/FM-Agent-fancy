import sys
import io
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.opencode_trace import _write_command_stdin

    # ---------------------------------------------------------------------------
    # Bug claim: if stream.close() itself raises, the function does NOT guarantee
    # the stream is closed, because the finally block propagates the close()
    # exception without catching it.
    #
    # Spec says: "stream is closed under all execution paths, including when an
    # exception is raised during writing or flushing"
    #
    # We confirm the bug by showing: when close() raises, the exception
    # propagates (the function doesn't handle it), meaning the post-condition
    # is not guaranteed under that execution path.
    # ---------------------------------------------------------------------------

    class FailingCloseStream:
        """Mock stream where close() raises to reveal the unhandled path."""
        close_attempted = False

        def __init__(self):
            self.written = None
            self.flushed = False

        def write(self, text):
            self.written = text

        def flush(self):
            self.flushed = True

        def close(self):
            FailingCloseStream.close_attempted = True
            raise IOError("simulated close failure")

    stream = FailingCloseStream()
    close_exception_caught = False

    try:
        _write_command_stdin(stream, "test-command")
    except IOError as e:
        close_exception_caught = True
        exception_message = str(e)

    # Spec requires the stream to be closed under ALL execution paths.
    # Here close() was attempted (the finally block ran) but it raised,
    # meaning the close did not complete. The exception propagated.
    # The post-condition "stream is closed" is not satisfied.
    bug_confirmed = FailingCloseStream.close_attempted and close_exception_caught

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_confirmed:
    print(
        f"CONFIRMED — close() was attempted but raised '{exception_message}'; "
        f"exception propagated unhandled, violating the spec that stream is "
        f"closed under all execution paths"
    )
else:
    print("NOT CONFIRMED — close() did not raise or exception was handled")
