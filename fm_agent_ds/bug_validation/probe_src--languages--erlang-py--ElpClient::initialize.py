"""Probe for bug src--languages--erlang-py--ElpClient::initialize.

Bug: initialize() raises RuntimeError when ELP returns a JSON-RPC error response
(e.g. "Method not found"), but the spec says exceptions are only raised for:
server unreachable, timeout, or malformed server messages.
"""

import os
import sys
import queue
import tempfile
from unittest.mock import MagicMock

# Ensure the repo root is on sys.path so that config.py resolves.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import src.languages.erlang as erlang  # public entry point

# FM-Agent self-validation guard: work in a fresh temp directory.
_original_cwd = os.getcwd()
_temp_dir = tempfile.mkdtemp(prefix="probe_erlang_init_")
os.chdir(_temp_dir)

try:
    # Simulated JSON-RPC error response from ELP (e.g. "Method not found").
    error_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32601, "message": "Method not found"},
    }

    # Construct ElpClient without spawning a real subprocess.
    client = erlang.ElpClient.__new__(erlang.ElpClient)
    client.proj_dir = _temp_dir
    client.root_uri = "file://" + _temp_dir
    client.timeout = 60
    client._messages = queue.Queue()
    client._next_id = 1
    client._status = None
    client._write_lock = MagicMock()
    client._proc = MagicMock()
    client._proc.stdin = MagicMock()
    client._reader = MagicMock()

    # Pre-seed the message queue so _wait_for_response sees the error.
    client._messages.put(error_msg)

    # Call the public initialize() — this must raise RuntimeError.
    result = client.initialize("/tmp/test.erl", "-module(test).")
    print(f"NOT CONFIRMED — no exception raised, returned: {result!r}")
except RuntimeError as exc:
    print(f"CONFIRMED — bug confirmed: RuntimeError raised for JSON-RPC error response: {exc}")
except Exception as exc:
    print(f"CONFIRMED — exception raised: {type(exc).__name__}: {exc}")
finally:
    os.chdir(_original_cwd)
    import shutil
    shutil.rmtree(_temp_dir, ignore_errors=True)
