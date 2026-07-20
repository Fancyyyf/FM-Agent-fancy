"""Probe script for bug: proc.terminate()/proc.kill() not exception-guarded in ElpClient.close()."""
import sys
import subprocess
from unittest.mock import Mock

sys.path.insert(0, ".")
from src.languages.erlang import ElpClient

# Create a bare ElpClient without actually starting an ELP subprocess.
# We only need the instance so we can call close().
client = ElpClient.__new__(ElpClient)

# Mount a mock subprocess.Popen that simulates a still-running process.
proc = Mock(spec=subprocess.Popen)
proc.stdin = Mock()
proc.stdout = Mock()
proc.poll.return_value = None          # process is still running → enter shutdown branch

# Make wait() raise TimeoutExpired so we reach the terminate() call.
proc.wait = Mock(side_effect=subprocess.TimeoutExpired(cmd=["mock"], timeout=5))

# The bug: terminate() raises because it's not wrapped in try/except.
proc.terminate = Mock(side_effect=OSError("No such process"))

client._proc = proc

# request() and notify() are patched so they raise immediately (caught by the
# existing except Exception: pass guards), avoiding a real LSP handshake.
client.request = Mock(side_effect=Exception("mock — bypass LSP"))
client.notify = Mock(side_effect=Exception("mock — bypass LSP"))

# Also ensure _write_lock exists (used by _send, which is called by notify
# via the patched methods — but request/notify are fully mocked so this is
# a safeguard).
import threading
client._write_lock = threading.Lock()

expected = "OSError"   # spec says no exception should propagate
passed = False

try:
    client.close()
    # If we reach here, no exception propagated — bug NOT confirmed.
    print("NOT CONFIRMED — close() completed without raising")
except OSError as exc:
    passed = True
    print(f"CONFIRMED — close() raised OSError: {exc}")
except Exception as exc:
    passed = True
    print(f"CONFIRMED — close() raised {type(exc).__name__}: {exc}")

# Also verify that the finally block still ran (proc set to None).
if passed and client._proc is None:
    pass  # correct - finally block ran despite the exception
elif passed:
    print("WARNING: finally block did not set _proc to None")
