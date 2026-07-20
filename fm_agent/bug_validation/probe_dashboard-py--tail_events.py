"""Probe script for dashboard-py--tail_events bug.

Bug: In State.tail_events(), the try/except only wraps json.loads(), so
if self._ingest_event(ev) raises, the exception propagates, the for-loop
exits prematurely, self._events_offset is NOT updated, and subsequent
JSONL lines are never processed — violating the spec guarantee that every
valid line must be ingested and the offset advanced to end-of-file.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add repo root so we can import dashboard as a public module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dashboard import State


class BugProbeState(State):
    """Subclass that simulates an _ingest_event failure on a chosen line."""

    def __init__(self, proj_dir: str, fail_on_line: int = 1):
        super().__init__(proj_dir)
        self._line_count = 0
        self._fail_on_line = fail_on_line
        self._ingested_events = []

    def _ingest_event(self, ev):
        self._line_count += 1
        self._ingested_events.append(ev)
        if self._line_count == self._fail_on_line:
            raise RuntimeError(f"SIMULATED_FAILURE on line {self._line_count}")


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = Path(tmpdir)
        trace_dir = proj_dir / "trace"
        trace_dir.mkdir(parents=True)
        events_path = trace_dir / "events.jsonl"

        # Write 3 valid JSON lines (line 2 will trigger the simulated failure)
        events = [
            {"type": "first", "n": 1},
            {"type": "second", "n": 2},
            {"type": "third", "n": 3},
        ]
        with open(events_path, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        file_size = events_path.stat().st_size

        # Create state with _ingest_event set to fail on line 2
        state = BugProbeState(str(proj_dir), fail_on_line=2)

        try:
            state.tail_events()
        except RuntimeError:
            pass  # Expected — _ingest_event raised

        actual_ingested = len(state._ingested_events)
        actual_offset = state._events_offset

        # Bug IS confirmed if:
        #   (a) not all lines were ingested (should be 3), AND
        #   (b) _events_offset was not advanced to file size
        bug_present = (actual_ingested != 3) and (actual_offset != file_size)

        if bug_present:
            print(
                f"CONFIRMED — _ingest_event failure on line 2 caused early exit. "
                f"ingested={actual_ingested}/3, offset={actual_offset} (expected {file_size})"
            )
        else:
            print(
                f"NOT CONFIRMED — all {actual_ingested} lines ingested, "
                f"offset={actual_offset} (expected {file_size})"
            )


if __name__ == "__main__":
    main()
