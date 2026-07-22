"""Probe script for ElpClient._handle_server_message bug.

Bug: When _handle_server_message receives an "elp/status" notification where
params lacks a "status" key, it sets self._status to None (via params.get("status")).
The specification requires self._status to remain unchanged in that scenario.

We exercise the bug through the public request() API, which calls
_wait_for_response → _handle_server_message for server-initiated messages
that do not match the pending request id.
"""
import sys
import os
import queue

try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.languages.erlang import ElpClient
    from unittest.mock import MagicMock

    client = ElpClient("/tmp/fake_proj_dir")
    # Set a known initial _status value
    EXPECTED_UNCHANGED = "INITIAL_VALUE"
    client._status = EXPECTED_UNCHANGED
    # Override timeout to a small value (avoids config dependency edge cases)
    client.timeout = 5
    # Prevent subprocess writes
    client._send = MagicMock()
    client._proc = MagicMock()

    # Build the message queue: first an "elp/status" notification without "status"
    # key, then a matching response so request() returns cleanly.
    msg_queue = queue.Queue()

    # Bug trigger: elp/status with params lacking "status" key
    msg_queue.put({
        "method": "elp/status",
        "params": {"irrelevant": "data"}
        # NOTE: no "status" key — spec says _status must NOT change
    })

    # Dummy response matching the request id so _wait_for_response returns
    msg_queue.put({
        "id": 1,
        "result": {}
    })
    client._messages = msg_queue

    # Exercise the buggy code path via the public API
    client.request("test/method")

    actual = client._status
    expected = EXPECTED_UNCHANGED
    passed = actual != expected  # True → bug confirmed (actual != expected)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
