"""Probe script for bug: src--languages--erlang-py--ElpClient::request

Bug: ElpClient.request() raises RuntimeError instead of TimeoutError when the
last retry receives ContentModifiedError after the overall deadline has expired.
The spec requires TimeoutError to take precedence over RuntimeError.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the repo root is on sys.path so 'src.languages.erlang' is importable.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.languages.erlang import ElpClient, _ContentModifiedError, _MAX_CONTENT_MODIFIED_RETRIES


try:
    # ------------------------------------------------------------------
    # Build a mock ElpClient that bypasses real __init__ (no subprocess).
    # ------------------------------------------------------------------
    client = object.__new__(ElpClient)
    client._messages = MagicMock()
    client._write_lock = MagicMock()
    client._proc = MagicMock()
    client._proc.stdin = MagicMock()
    client._next_id = 1
    client.timeout = 10  # deadline = monotonic(0) + 10.0 = 10.0

    # _send is a no-op; we only care about control flow after the error.
    client._send = MagicMock()

    # _wait_for_response always signals a content-modified error so every
    # attempt fails.
    content_error = _ContentModifiedError({"code": -32801, "message": "content modified"})
    client._wait_for_response = MagicMock(side_effect=content_error)

    # ------------------------------------------------------------------
    # Control time.monotonic() so that:
    #   - deadline = 0 + 10 = 10
    #   - attempts 0-3 see remaining > 0  → sleep and retry
    #   - by attempt 4 (the 5th), monotonic ≥ 11  →  deadline expired
    # ------------------------------------------------------------------
    monotonic_values = [0.0, 5.0, 6.0, 7.0, 8.0, 11.0]
    monotonic_idx = [0]

    def mock_monotonic():
        idx = min(monotonic_idx[0], len(monotonic_values) - 1)
        value = monotonic_values[idx]
        monotonic_idx[0] += 1
        return value

    # ------------------------------------------------------------------
    # Run the request and capture which exception type propagates.
    # ------------------------------------------------------------------
    actual_type = None
    with patch("src.languages.erlang.time.monotonic", mock_monotonic), \
         patch("src.languages.erlang.time.sleep", MagicMock()):
        try:
            client.request("test/method", {"key": "value"})
        except RuntimeError:
            actual_type = RuntimeError
        except TimeoutError:
            actual_type = TimeoutError
        except Exception as e:
            actual_type = type(e)

    # Spec says TimeoutError should win when the deadline has expired.
    # The code raises RuntimeError (bug) because it skips the remaining check
    # on the last attempt.
    expected_type = TimeoutError
    bug_reproduced = actual_type != expected_type

    if bug_reproduced:
        print(
            f"CONFIRMED — actual: {actual_type.__name__} raised "
            f"| expected: TimeoutError | deadline=10.0, "
            f"monotonic_reached={monotonic_values[-1]}, deadline expired on final retry"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual_type.__name__}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
