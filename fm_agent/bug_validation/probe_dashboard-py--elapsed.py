import os
import sys

# Ensure the repo root is on sys.path so that `dashboard` is importable
# when the script is run from the repo root.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from datetime import datetime, timezone

try:
    from dashboard import State
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

def main():
    try:
        # Create a minimal State instance. _locate_workdir() falls back to
        # project_root / "fm_agent" which exists under the snapshot.
        state = State(_repo_root)

        # Set first_event_time to a non-None value so elapsed() does not
        # return early at the None guard.
        state.first_event_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Simulate the "absent" case described in the trigger condition:
        # delete the last_event_time attribute entirely.
        del state.last_event_time

        # Call elapsed(). If the bug exists, this raises AttributeError
        # because line 508 accesses self.last_event_time directly.
        result = state.elapsed()
        print(f'NOT CONFIRMED — elapsed() returned {result!r} despite absent last_event_time')

    except AttributeError as e:
        # Bug confirmed: code crashes when last_event_time attribute is absent,
        # violating the spec which says the method should handle "absent" gracefully.
        print(f'CONFIRMED — AttributeError when last_event_time is absent: {e}')
    except Exception as e:
        print(f'ERROR: unexpected {type(e).__name__}: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
