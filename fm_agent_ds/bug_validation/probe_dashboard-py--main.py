"""Probe for dashboard-py--main: verify that State methods handle missing trace_dir gracefully.

Spec claim: When trace_dir does not exist, print to stderr and continue (enter loop).
Reported bug: state.tail_events() raises FileNotFoundError when trace_dir is missing.
"""

import os
import sys
import tempfile

# Import via public entry point (dashboard.py at repo root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dashboard import State


def main():
    # Create a truly empty temp directory with no trace/ subdirectory
    tmp = tempfile.mkdtemp(prefix="probe_dashboard_")
    try:
        state = State(tmp)

        # Precondition check: trace_dir should not exist
        if state.trace_dir.exists():
            print("ERROR: trace_dir unexpectedly exists at", state.trace_dir)
            sys.exit(1)

        errors = []

        # Test tail_events — spec says this should NOT crash
        try:
            state.tail_events()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"tail_events raised {type(e).__name__}: {e}")

        # Test tail_opencode — spec says this should NOT crash
        try:
            state.tail_opencode()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"tail_opencode raised {type(e).__name__}: {e}")

        # Test scan_bugs — spec says this should NOT crash
        try:
            state.scan_bugs()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"scan_bugs raised {type(e).__name__}: {e}")

        if errors:
            print("CONFIRMED — state methods raised exceptions on missing trace_dir:")
            for e in errors:
                print(f"  {e}")
        else:
            print(
                "NOT CONFIRMED — all state methods (tail_events, tail_opencode, scan_bugs) "
                "handled missing trace_dir gracefully without raising exceptions"
            )

    finally:
        # Cleanup temp directory
        import shutil
        try:
            shutil.rmtree(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    main()
