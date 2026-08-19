"""Probe for dashboard-py--State::tail_events bug: Path.exists() on a directory
does not trigger early return, leading to IsADirectoryError instead of the required
normal return with no side effects."""

import sys
import tempfile
import os
from pathlib import Path

# Add repo root to path so we can import dashboard
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import State
except Exception as e:
    print(f"ERROR: Failed to import dashboard.State: {e}")
    sys.exit(1)

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a trace directory inside tmpdir
        trace_dir = tmpdir_path / "trace"
        trace_dir.mkdir()

        # Create a directory named "events.jsonl" (not a file)
        # This simulates the bug trigger: events_path is a directory
        fake_events_path = trace_dir / "events.jsonl"
        fake_events_path.mkdir()

        # Also create opencode dir (required by State init)
        opencode_dir = trace_dir / "opencode"
        opencode_dir.mkdir()

        # Create State with proj_dir = tmpdir_path
        # This sets workdir = tmpdir_path (since tmpdir_path/trace exists)
        # and events_path = trace_dir / "events.jsonl" = fake_events_path (a directory)
        state = State(str(tmpdir_path))

        # Verify the events_path is indeed a directory
        if not state.events_path.is_dir():
            print(f"NOT CONFIRMED — events_path is not a directory: {state.events_path}")
        else:
            # Attempt tail_events() — the buggy code should raise IsADirectoryError
            # because Path.exists() returns True for directories
            try:
                state.tail_events()
                # If we get here without an exception, the code handled it somehow
                # But the spec says should return with no side effects, so check if
                # anything was modified (though for a directory, there's nothing to read)
                print("NOT CONFIRMED — tail_events() returned normally instead of raising an exception")
            except IsADirectoryError:
                print(f"CONFIRMED — tail_events() raised IsADirectoryError when events_path is a directory; "
                      f"spec requires normal return with no side effects")
            except OSError as e:
                if "Is a directory" in str(e) or "directory" in str(e).lower():
                    print(f"CONFIRMED — tail_events() raised OSError ({type(e).__name__}: {e}) "
                          f"when events_path is a directory; spec requires normal return with no side effects")
                else:
                    print(f"ERROR: Unexpected OSError: {e}")
                    sys.exit(1)
            except Exception as e:
                print(f"ERROR: {e}")
                sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
