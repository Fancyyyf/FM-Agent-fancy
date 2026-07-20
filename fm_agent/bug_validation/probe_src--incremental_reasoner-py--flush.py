import sys
import io

try:
    from src.incremental_reasoner import _StdoutTee

    class FlakyConsole:
        """Console whose flush() raises OSError, simulating a device-level flush failure."""

        def __init__(self):
            self.written = []

        def write(self, data):
            self.written.append(data)
            return len(data)

        def flush(self):
            raise OSError("Simulated flush failure")

    console = FlakyConsole()
    log_stream = io.StringIO()

    # Ensure the log_stream appears open so we reach line 90
    tee = _StdoutTee(console, log_stream)

    # Write some data through the tee so there IS buffered data that needs flushing
    tee.write("buffered data\n")

    # Call flush() — the spec claims all buffered console data is guaranteed delivered.
    # If _console.flush() raises an unhandled exception, the spec guarantee is violated.
    exception_propagated = False
    try:
        tee.flush()
    except OSError:
        exception_propagated = True
    except Exception as e:
        print(f"ERROR: Unexpected exception type: {type(e).__name__}: {e}")
        sys.exit(1)

    if exception_propagated:
        print(
            "CONFIRMED — self._console.flush() raised OSError and the exception "
            "propagated unhandled; the specification guarantee (all buffered console "
            "data delivered) is violated."
        )
    else:
        print(
            "NOT CONFIRMED — self._console.flush() exception was handled within "
            "flush(); the specification guarantee may still hold."
        )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
