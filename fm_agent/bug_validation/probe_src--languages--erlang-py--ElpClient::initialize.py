"""Probe for ElpClient.initialize bug: deadline computed after request(), not from call entry."""

import os
import sys
import tempfile
import time

bug_id = "src--languages--erlang-py--ElpClient::initialize"

# Ensure the repo root is on sys.path so we can import the package.
repo_root = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../..")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Create a fresh temporary workspace for all fixtures and artifacts.
workspace = tempfile.mkdtemp(prefix="bug_probe_", dir="/tmp")
os.chdir(workspace)

try:
    from src.languages.erlang import ElpClient

    client = ElpClient(workspace)
    client.timeout = 1.0  # known short timeout for deterministic test

    # Override request(): simulate a slow LSP initialize handshake that
    # consumes most of the timeout budget before the deadline is even set.
    def fake_request(method, params=None):
        time.sleep(0.6)  # 60% of the 1s timeout wasted before deadline is computed
        return {"serverInfo": {"name": "elp", "version": "1.0"}}

    client.request = fake_request

    # Remaining methods must be no-ops so we don't hit real I/O.
    client.notify = lambda method, params=None: None
    client.open_document = lambda path, source=None: None

    # _handle_server_message is a no-op; we control status directly in _next_message.
    client._handle_server_message = lambda msg: None

    # Override _next_message to capture the deadline and transition status to "running".
    captured_deadlines = []

    def capture_next_message(deadline):
        captured_deadlines.append(deadline)
        # Simulate an elp/status notification that makes the while-loop exit.
        client._status = "running"
        return {"method": "elp/status", "params": {"status": "running"}}

    client._next_message = capture_next_message

    entry_time = time.monotonic()
    client.initialize("/tmp/bootstrap.erl", "-module(bootstrap).")

    if len(captured_deadlines) == 0:
        print("NOT CONFIRMED — _next_message was never called")
        sys.exit(0)

    actual_deadline = captured_deadlines[0]
    expected_deadline = entry_time + client.timeout

    # The spec requires the deadline to be measured from call entry.
    # The buggy code measures it after request(), so actual_deadline is
    # entry_time + request_delay + timeout instead of entry_time + timeout.
    tolerance = 0.2  # allow for slight timing jitter
    if actual_deadline > expected_deadline + tolerance:
        delta = actual_deadline - expected_deadline
        print(
            f"CONFIRMED — actual deadline: {actual_deadline:.3f}"
            f" > expected: {expected_deadline:.3f}"
            f" (delta: {delta:.3f}s, spec requires deadline from call entry)"
        )
    else:
        print(
            f"NOT CONFIRMED — actual deadline {actual_deadline:.3f}"
            f" <= expected {expected_deadline:.3f} (+{tolerance}s tolerance)"
        )

except ImportError as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    import shutil
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        pass
