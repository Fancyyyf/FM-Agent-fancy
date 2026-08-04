"""Probe script for bug: ElpClient._wait_for_response - empty error dict bypasses error handling.

Bug ID: src--languages--erlang-py--ElpClient::_wait_for_response
Source: src/languages/erlang.py, line 186: `if error:` treats empty dict {} as falsy.
Spec: Any error object other than ContentModifiedError must raise RuntimeError.
Bug: Empty error dict {} is falsy, so error handling is skipped and message.get("result") is returned.
"""
import sys
import time

try:
    from src.languages.erlang import ElpClient

    # Create an ElpClient instance without starting a subprocess.
    # We avoid __enter__ to not require ELP to be installed.
    client = ElpClient("/tmp/fake_proj_dir")

    # Craft a JSON-RPC response message that matches request_id=1,
    # has no "method" key, and contains an empty error dict {}.
    # An empty dict is falsy in Python, which triggers the bug.
    crafted_response = {"jsonrpc": "2.0", "id": 1, "error": {}, "result": None}

    # Monkey-patch _next_message to return the crafted response
    # so we can exercise _wait_for_response without a real ELP server.
    original_next_message = client._next_message
    client._next_message = lambda deadline: crafted_response

    try:
        actual = client._wait_for_response(1, time.monotonic() + 10)
        # If we reach here, no exception was raised — the bug is confirmed.
        # The spec demands RuntimeError for any error that isn't _ContentModifiedError.
        passed = True  # Bug reproduced: empty error dict bypassed error handling
    except RuntimeError as e:
        # The code correctly raised a RuntimeError (bug NOT confirmed / already fixed)
        actual = f"RuntimeError: {e}"
        passed = False
    except Exception as e:
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        # Restore original method
        client._next_message = original_next_message

    expected = "RuntimeError for any non-content-modified error object"

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
