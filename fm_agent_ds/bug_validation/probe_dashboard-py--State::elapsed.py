import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

# Add repo root to sys.path so 'import dashboard' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from dashboard import State

    # Create probe workspace under a fresh temp directory (self-validation guard)
    probe_tmp = tempfile.mkdtemp(prefix="probe_elapsed_")

    # Instantiate State — uses the temp dir which has no trace/ subdir,
    # so _locate_workdir returns <tempdir>/fm_agent (no write occurs)
    state = State(probe_tmp)

    # Trigger condition: last_event_time earlier than first_event_time
    future_time = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)
    past_time   = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)

    state.first_event_time = future_time
    state.last_event_time  = past_time

    actual   = state.elapsed()
    # Specification requires non-negative float; negative result = bug confirmed
    expected = abs(future_time - past_time).total_seconds()  # what should be reported
    passed   = actual < 0  # True → bug reproduced (negative elapsed returned)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Clean up temp directory
    try:
        os.rmdir(probe_tmp)
    except Exception:
        pass

if passed:
    print(f'CONFIRMED — actual: {actual!r} (negative) | expected: {expected!r} (non-negative) | '
          f'bug: elapsed() returns negative when last_event_time < first_event_time')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
