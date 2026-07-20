import os
import sys
import time as time_module
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add repo root to sys.path so `import dashboard` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

sys.argv = ['dashboard.py', '/tmp/nonexistent_test_dir', '--refresh', '2.0']

sleep_calls = []

def mock_sleep(duration):
    sleep_calls.append(duration)
    raise KeyboardInterrupt()

time_module.sleep = mock_sleep

try:
    import dashboard

    mock_state = MagicMock()
    mock_state.trace_dir.exists.return_value = False
    mock_state.elapsed.return_value = None

    with patch.object(dashboard, 'State', return_value=mock_state):
        with patch.object(dashboard, 'Console'):
            with patch.object(dashboard, 'Live'):
                with patch.object(dashboard, 'build_layout', return_value=MagicMock()):
                    dashboard.main()
except KeyboardInterrupt:
    pass
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

spec_max_sleep = 1.0  # spec: "no slower than once per second" → sleep ≤ 1.0

if not sleep_calls:
    print('ERROR: time.sleep was never called')
    sys.exit(1)

actual_sleep = sleep_calls[0]
bug_present = actual_sleep > spec_max_sleep

if bug_present:
    print(f'CONFIRMED — time.sleep called with {actual_sleep}s, spec requires ≤ {spec_max_sleep}s')
else:
    print(f'NOT CONFIRMED — time.sleep called with {actual_sleep}s, within spec limit of {spec_max_sleep}s')
