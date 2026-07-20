import sys
import os
import queue
import time

# Ensure the repo root is on sys.path so 'src.languages.erlang' resolves.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import ElpClient

    # Create an ElpClient instance with a temporary proj_dir. We never start
    # a subprocess, so the internal state is all we need for the test.
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        client = ElpClient(tmpdir)

        # Place a message in the queue BEFORE calling _next_message, simulating
        # a message that arrived ahead of the deadline check.
        test_message = {"jsonrpc": "2.0", "id": 1, "result": "hello"}
        client._messages.put(test_message)

        # deadline = current monotonic time → remaining <= 0
        deadline = time.monotonic()
        expected = test_message

        try:
            actual = client._next_message(deadline)
        except TimeoutError:
            actual = TimeoutError  # sentinel for "TimeoutError was raised"

        # Bug reproduced if TimeoutError was raised despite a queued message
        passed = actual is TimeoutError

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: TimeoutError raised | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
