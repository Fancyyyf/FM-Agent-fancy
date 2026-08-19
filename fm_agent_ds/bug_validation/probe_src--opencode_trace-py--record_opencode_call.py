"""Probe for record_opencode_call: summary=None should store None, not f"OpenCode {stage}"."""
import sys
import tempfile
import os
from unittest.mock import patch

try:
    # Load via package entry point — import the internal function from the package module
    from src.opencode_trace import record_opencode_call

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = tmpdir
        captured_event = {}

        def fake_record_trace_event(trace_dir, event):
            captured_event.update(event)

        with (
            patch("src.opencode_trace.record_trace_event", side_effect=fake_record_trace_event),
            patch("os.path.exists", return_value=False),
        ):
            record_opencode_call(
                work_dir=work_dir,
                event_id="test_evt_001",
                stage="build",
                status="success",
                started="2025-01-01T00:00:00Z",
                ended="2025-01-01T00:01:00Z",
                command="opencode run",
                summary=None,            # Omitted — spec says store empty default
                function_ids=None,
                input_files=None,
                output_files=None,
                exit_code=0,
                error=None,
                metadata=None,
                opencode_log_path=None,
                opencode_trace_path=None,
            )

        actual_summary = captured_event.get("summary")
        expected_summary = None       # spec: omitted optional → empty default

        passed = actual_summary != expected_summary

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual summary: {actual_summary!r} | expected: {expected_summary!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_summary!r}")
