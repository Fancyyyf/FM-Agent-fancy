import sys
import os

# Ensure the repo root is on sys.path so that config.py and src/* resolve.
# The probe runs from the repo root, so os.getcwd() points there.
sys.path.insert(0, os.getcwd())

try:
    from src.incremental_reasoner import _StdoutTee
except Exception as e:
    print(f"ERROR: failed to import _StdoutTee: {e}")
    sys.exit(1)


class RaisingConsole:
    """A mock console stream that raises OSError on write()."""

    def write(self, data):
        raise OSError("Simulated console write failure")

    def flush(self):
        pass


class MockLogStream:
    """A mock log stream with a writable stream and a closed flag."""

    def __init__(self, closed=False):
        self.closed = closed
        self._written = []

    def write(self, data):
        self._written.append(data)

    def flush(self):
        pass


def main():
    console = RaisingConsole()
    log_stream = MockLogStream(closed=False)

    tee = _StdoutTee(console, log_stream)

    # Per the specification the console write must deliver data and the
    # method must return len(data).  If the console raises, the code propagates
    # the exception — data is NOT delivered and len(data) is NOT returned.
    try:
        result = tee.write("hello")
        # Reaching here means the console write did NOT raise —
        # the bug is not triggered (NOT CONFIRMED).
        print(f"NOT CONFIRMED — write returned: {result!r}")
    except OSError:
        # The exception propagated — the spec post-condition (delivery to console,
        # return len(data)) is violated.
        print("CONFIRMED — exception propagated from _StdoutTee.write() "
              "when console.write() raises; data not delivered to console "
              "and len(data) not returned")
    except Exception as e:
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
