"""Probe for ElpClient._next_message bug: returns non-dict values without validation."""

import os
import queue
import sys
import tempfile
import time

# Ensure the repo root is on sys.path so we can import the package.
repo_root = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../..")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Create a fresh temporary workspace for all fixtures and artifacts.
workspace = tempfile.mkdtemp(prefix="bug_probe_", dir="/tmp")
os.chdir(workspace)

try:
    from src.languages.erlang import ElpClient

    # Spec claim: _next_message must return a dict conforming to JSON-RPC 2.0,
    # or raise TimeoutError/RuntimeError.

    # Trigger condition: the queue contains a non-dict, non-BaseException value
    # (e.g., a list). The code returns it without checking that it is a dict.

    # Create an ElpClient in a temp dir — __init__ only sets up attributes,
    # it does not spawn ELP.
    client = ElpClient(workspace)
    actual = None
    passed = False

    # Put a non-dict value (a list) into the internal message queue.
    buggy_payload = [1, 2, 3]  # not a dict
    client._messages.put(buggy_payload)

    # Set a deadline far in the future to avoid TimeoutError.
    deadline = time.monotonic() + 30.0

    actual = client._next_message(deadline)

    # BUG: _next_message returned a list, violating the spec that says it
    # must return a dict conforming to JSON-RPC 2.0.
    if not isinstance(actual, dict):
        passed = True
        print(f"CONFIRMED — actual: {actual!r} (type: {type(actual).__name__}) | expected: dict conforming to JSON-RPC 2.0")
    else:
        print(f"NOT CONFIRMED — actual matched expected type: {actual!r}")

except ImportError as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Clean up the temporary workspace.
    import shutil
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        pass
