import sys
import tempfile
import shutil
from pathlib import Path

# Ensure the repo root is on the module search path so "from dashboard ..." resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from dashboard import State
except Exception as e:
    print(f'ERROR: import dashboard failed — {e}')
    sys.exit(1)

tmpdir = Path(tempfile.mkdtemp())
try:
    state = State(str(tmpdir))

    # Reproduce the bug: set bugs_pending to a non-zero value, then call
    # scan_bugs() when bug_dir does not exist. The spec says all three
    # counters must become zero, but the code returns early without
    # resetting bugs_pending.
    state.bugs_pending = 5

    # Also confirm the other two ARE reset, proving only 'pending' is missed
    state.bugs_confirmed = 999
    state.bugs_not_confirmed = 999

    state.scan_bugs()

    # After scan_bugs() with a missing bug_dir, the spec requires:
    #   bugs_confirmed == 0, bugs_not_confirmed == 0, bugs_pending == 0
    expected_pending = 0
    actual_pending = state.bugs_pending

    # The bug is confirmed when actual_pending != expected_pending
    # i.e., bugs_pending was NOT reset to 0
    bug_reproduced = actual_pending != expected_pending

    if bug_reproduced:
        print(
            f'CONFIRMED — bugs_pending: {actual_pending} (should be {expected_pending}), '
            f'bugs_confirmed: {state.bugs_confirmed}, '
            f'bugs_not_confirmed: {state.bugs_not_confirmed}'
        )
    else:
        print(
            f'NOT CONFIRMED — bugs_pending matched expected: {actual_pending}, '
            f'bugs_confirmed: {state.bugs_confirmed}, '
            f'bugs_not_confirmed: {state.bugs_not_confirmed}'
        )
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
