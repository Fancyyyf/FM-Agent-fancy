"""Probe script for dashboard-py--_locate_workdir: verify workspace detection
uses trace data presence, not just trace/ subdirectory existence."""
import sys
import os

# Probe lives at fm_agent/bug_validation/ — two levels deep from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tempfile
from pathlib import Path

try:
    import dashboard

    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate a workspace directory that contains trace output data
        # as a *file* named "trace" — not a subdirectory.
        (Path(tmpdir) / "trace").write_text("dummy trace data")

        # The public API: dashboard.State.__init__ calls _locate_workdir internally.
        # Expected (spec): workdir resolves to tmpdir verbatim because trace
        # output data exists there.
        # Actual (buggy): workdir resolves to tmpdir / "fm_agent" because the
        # code only checks for a trace/ subdirectory.
        state = dashboard.State(tmpdir)

        expected = Path(tmpdir).resolve()
        actual = state.workdir.resolve()

        # Bug confirmed if actual != expected (code fell through to append "fm_agent")
        passed = actual != expected

        if passed:
            print(
                f"CONFIRMED — spec: resolve to workspace dir ({expected}) when "
                f"trace data present, but code returned {actual} (appended fm_agent)"
            )
        else:
            print(f"NOT CONFIRMED — workdir matches expected: {actual}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
