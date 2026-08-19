"""Probe script for bug src--languages--erlang-py--ElpClient::close

Verifies that ElpClient.close() leaves self._reader active (not stopped/joined),
violating the spec claim that the reader thread should be stopped.
"""

import os
import sys
import threading
import tempfile

# Add repo root to sys.path so project imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.languages.erlang import ElpClient


class MockStream:
    """Mock for subprocess stdin/stdout — supports write, flush, close."""

    def write(self, data: bytes) -> int:
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class MockProcess:
    """Mock for subprocess.Popen — simulates a process that has already exited."""

    def __init__(self) -> None:
        self.stdin = MockStream()
        self.stdout = MockStream()

    def poll(self) -> int:
        return 0  # Process already exited → close() skips shutdown/terminate


def main() -> None:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            client = ElpClient(proj_dir=tmpdir)

            # Create a trackable background reader thread (simulating _JsonRpcReader)
            reader_running = threading.Event()
            # Event starts clear — the thread will block on wait(), staying alive

            def reader_worker() -> None:
                reader_running.wait()

            reader = threading.Thread(target=reader_worker, daemon=True)
            reader.start()

            # Wire up the mock process and reader thread
            client._proc = MockProcess()
            client._reader = reader

            # ---- Exercise the buggy code path ----
            client.close()

            # ---- Verify state against the spec claim ----
            proc_is_none = client._proc is None
            reader_is_none = client._reader is None
            reader_alive = reader.is_alive()

            # SPEC says: reader stopped/joined, _reader set to None
            # ACTUAL (bug): _reader still alive and not None
            bug_confirmed = proc_is_none and reader_alive and not reader_is_none

            if bug_confirmed:
                print(
                    f"CONFIRMED — _proc is None={proc_is_none}, "
                    f"_reader is alive={reader_alive}, "
                    f"_reader is None={reader_is_none}"
                )
            else:
                print(
                    f"NOT CONFIRMED — _proc is None={proc_is_none}, "
                    f"_reader is alive={reader_alive}, "
                    f"_reader is None={reader_is_none}"
                )

            # Cleanup the reader thread
            reader_running.clear()
            reader.join(timeout=2)

    except Exception as exc:
        import traceback

        print(f"ERROR: {exc}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
