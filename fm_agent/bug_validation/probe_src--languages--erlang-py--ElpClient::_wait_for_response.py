"""Probe script for ElpClient._wait_for_response bug.

Bug: When a JSON-RPC response carries "error": null, the code checks
truthiness with `if error:` (line 186 of src/languages/erlang.py) and
fall through to `return message.get("result")` instead of raising
RuntimeError as the specification requires.
"""

import sys
import os

# Ensure the repo root is on the path so the package entry point resolves.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tempfile
import queue
import time

try:
    from src.languages.erlang import ElpClient
except Exception as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)

# ── Construct a minimal ElpClient without launching ELP ──────────────────
client = ElpClient(tempfile.mkdtemp(prefix="fm-agent-probe-"))

# Seed the message queue with a matching JSON-RPC response whose "error"
# field is explicitly null (Python None).  The spec requires this to raise
# RuntimeError; the buggy code will return the "result" value instead.
request_id = 42
deadline = time.monotonic() + 10.0

client._messages.put({
    "jsonrpc": "2.0",
    "id": request_id,
    "error": None,          # ← null in JSON-RPC → None in Python
    "result": "some_value",
})
# No "method" key → the response is recognised as a server response.

# ── Exercise the buggy code path ────────────────────────────────────────
actual = None
raised = None

try:
    actual = client._wait_for_response(request_id, deadline)
except RuntimeError as exc:
    raised = exc
except Exception as exc:
    print(f"ERROR: Unexpected exception: {exc}")
    sys.exit(1)

# ── Oracle ──────────────────────────────────────────────────────────────
# Specification: "When the matching response contains an 'error' field …
#   Otherwise: raises RuntimeError whose message includes a description of
#               the error"
# Bug: the code returns result when error is None (falsy).
#
# If `_wait_for_response` returned a value (actual is not None and no
# exception) → the bug is **CONFIRMED** because the spec requires a raise.
#
# If it raised RuntimeError → NOT CONFIRMED (the code behaves correctly
# for this input).

if raised is None and actual is not None:
    # Bug reproduced: code returned result instead of raising.
    print(f"CONFIRMED — actual returned: {actual!r} | expected: RuntimeError (per spec)")
else:
    print(f"NOT CONFIRMED — actual raised: {raised!r}")
