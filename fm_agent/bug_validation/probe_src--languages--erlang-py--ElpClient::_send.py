"""Probe script for bug: src--languages--erlang-py--ElpClient::_send

Bug: ElpClient._send() raises OSError (BrokenPipeError) instead of RuntimeError
when the server process has exited but self._proc is not None. The spec requires
RuntimeError when the server process is not running; the code only checks for
None values, not whether the process is alive via poll().
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure the repo root is on sys.path so 'src.languages.erlang' is importable.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.languages.erlang import ElpClient


try:
    # ------------------------------------------------------------------
    # Build a mock ElpClient that bypasses real __init__ (no subprocess).
    # Set up self._proc: not None, stdin not None, but poll() shows exited.
    # This simulates: the ELP server process terminates unexpectedly, but
    # the Popen object and its stdin pipe still exist.
    # ------------------------------------------------------------------
    client = object.__new__(ElpClient)
    client._write_lock = MagicMock()

    mock_proc = MagicMock()
    mock_proc.poll.return_value = 0          # Process has exited (return code 0)
    mock_proc.stdin = MagicMock()
    # Writing to a dead process's stdin raises BrokenPipeError on Linux
    mock_proc.stdin.write.side_effect = BrokenPipeError

    client._proc = mock_proc

    # ------------------------------------------------------------------
    # Exercise _send through the public API: notify().
    # ------------------------------------------------------------------
    actual_type = None
    try:
        client.notify("test/method", {"key": "value"})
    except RuntimeError:
        actual_type = RuntimeError
    except BrokenPipeError:
        actual_type = BrokenPipeError
    except OSError:
        actual_type = OSError
    except Exception as e:
        actual_type = type(e)

    # Spec says: "If the server process is not running or its stdin stream
    # is not writable, raises RuntimeError."
    # The code only checks for None, so it proceeds to write and gets
    # BrokenPipeError (a subclass of OSError) instead of RuntimeError.
    expected_type = RuntimeError
    bug_reproduced = actual_type != expected_type

    if bug_reproduced:
        print(
            f"CONFIRMED — actual: {actual_type.__name__} raised "
            f"| expected: RuntimeError | process exited (poll()=0) but "
            f"self._proc is not None, so None check passes; write to dead "
            f"pipe raises {actual_type.__name__} instead of RuntimeError"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual_type.__name__}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
