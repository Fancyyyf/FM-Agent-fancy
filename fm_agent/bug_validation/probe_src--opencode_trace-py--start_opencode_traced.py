import sys
import os
from unittest.mock import MagicMock, patch

# Let src be importable from repo root
sys.path.insert(0, os.getcwd())

def _dummy_start_opencode_process(*args, **kwargs):
    """Mock that returns a fake proc and live threads."""
    mock_proc = MagicMock()
    mock_log_thread = MagicMock()
    mock_log_thread.is_alive.return_value = True
    mock_stdin_thread = MagicMock()
    mock_stdin_thread.is_alive.return_value = True
    return mock_proc, mock_log_thread, mock_stdin_thread

try:
    with patch(
        "src.opencode_trace._start_opencode_process",
        side_effect=_dummy_start_opencode_process,
    ):
        from src.opencode_trace import start_opencode_traced

        result = start_opencode_traced(
            proj_dir="/tmp/test_proj",
            work_dir="/tmp/test_work",
            command=["opencode", "run", "--", "echo", "hello"],
            stage="test",
        )

    event_id = result.event_id

    # Spec requires event_id to start with "opencode_"
    passed = event_id.startswith("opencode_")

    if passed:
        print(f"NOT CONFIRMED — event_id starts with opencode_: {event_id!r}")
    else:
        print(f"CONFIRMED — event_id does NOT start with opencode_: {event_id!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
