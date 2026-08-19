#!/usr/bin/env python3
"""Probe: path traversal in _opencode_log_path via malicious event_id.

Bug: _opencode_log_path does not sanitize event_id, allowing path traversal
when event_id contains "../" sequences. The spec requires the returned path
to stay within the trace directory structure.

Public API: from src.opencode_trace import _opencode_log_path
"""

import os
import sys
import tempfile


def main():
    # Add repo root to path so that 'from src.opencode_trace import ...' works
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    try:
        from src.opencode_trace import _opencode_log_path  # type: ignore
    except ImportError as exc:
        print(f"ERROR: Cannot import _opencode_log_path: {exc}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = os.path.join(tmpdir, "run")
        os.makedirs(work_dir, exist_ok=True)

        # Establish the expected trace boundaries
        trace_dir = os.path.join(work_dir, "trace")
        payload_dir = os.path.join(trace_dir, "payloads")
        os.makedirs(payload_dir, exist_ok=True)

        # Call with a path-traversal event_id
        event_id = "../../malicious"
        try:
            actual_path = _opencode_log_path(work_dir, event_id)
        except Exception as exc:
            print(f"ERROR: _opencode_log_path raised: {exc}")
            sys.exit(1)

        # Resolve both to canonical absolute paths for comparison
        actual_abs = os.path.realpath(actual_path)
        # The spec says the path must stay within the trace directory structure
        trace_abs = os.path.realpath(trace_dir)

        # A correct path would be under trace_abs; a traversed path won't be
        within_trace = os.path.commonpath([actual_abs, trace_abs]) == trace_abs

        if not within_trace:
            print(
                f"CONFIRMED — path traversal successful\n"
                f"  work_dir:      {work_dir}\n"
                f"  trace_dir:     {trace_dir}\n"
                f"  expected_under: {trace_abs}\n"
                f"  actual_path:   {actual_abs}\n"
                f"  event_id:      {event_id!r}\n"
                f"  escaped trace directory"
            )
        else:
            print(f"NOT CONFIRMED — path remained within trace directory: {actual_abs}")


if __name__ == "__main__":
    main()
