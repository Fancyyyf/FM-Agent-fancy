"""Probe script for ElpClient._handle_server_message bug.

Bug: When message has method="elp/status" but NO "params" key, the spec says
self._status should NOT be updated. The code defaults missing params to {},
causing self._status to be unconditionally set to None (via {}.get("status")),
violating the specification.

FM-Agent self-validation: tests the smallest unit (ElpClient instance without
starting ELP subprocess), per the self-validation guard.
"""

import sys
import os
import tempfile

# Add repo root to Python path so the 'src' package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.languages.erlang import ElpClient

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an ElpClient without starting it (no __enter__).
        # __init__ sets _status to None via normal flow, so we must
        # reassign to a sentinel before the test call.
        client = ElpClient(os.path.join(tmpdir, "dummy_proj"))

        # Set _status to a known sentinel value to detect overwrite
        client._status = "INITIAL_SENTINEL"

        # Message: method="elp/status", no "params" key, no "id" key
        # Spec: _status should NOT change (requires "params" key present)
        # Code (buggy): _status gets set to None when "params" key is absent
        message = {"method": "elp/status"}

        client._handle_server_message(message)

        # Per spec: _status should remain "INITIAL_SENTINEL" when "params" is absent
        # Per code: _status is overwritten to None
        if client._status == "INITIAL_SENTINEL":
            print(
                "NOT CONFIRMED — _status remained unchanged ('INITIAL_SENTINEL') "
                "when 'params' key was absent, which matches the specification."
            )
        else:
            print(
                f"CONFIRMED — _status was overwritten to {client._status!r} from "
                f"'INITIAL_SENTINEL' despite the message lacking a 'params' key. "
                f"The specification requires _status to be updated ONLY when the "
                f"message contains a 'params' key."
            )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
