#!/usr/bin/env python3
"""Probe for finish_opencode_trace: stderr_thread not joined before trace event commit.

Spec claim: Every background thread responsible for capturing process output
has terminated and flushed before the trace event is committed.

Actual behavior: Only stdin_thread and log_thread are joined.
Any other output-capturing thread (e.g. stderr_thread) is not awaited.
"""
import sys
import threading
import types

sys.path.insert(0, '/home/fancy/Projects_Vault/FM-Agent')

import src.opencode_trace as target

def main():
    try:
        # Create a dummy thread and track whether its join() is called
        stderr_joined_flag = threading.Event()

        def stderr_worker():
            pass

        stderr_thread = threading.Thread(target=stderr_worker, daemon=True)

        original_join = stderr_thread.join
        def tracked_join(timeout=None):
            stderr_joined_flag.set()
            original_join(timeout=timeout)
        stderr_thread.join = tracked_join

        # Build a record mirroring TracedOpenCodeProcess but with stderr_thread
        record = types.SimpleNamespace()
        record.stdin_thread = None
        record.log_thread = None
        record.stderr_thread = stderr_thread  # hypothetical output-capture thread

        # Fake proc
        proc = types.SimpleNamespace()
        proc.returncode = 0
        record.proc = proc

        # Remaining fields required by finish_opencode_trace / record_opencode_call
        record.error = None
        record.work_dir = "/tmp"
        record.event_id = "test_event"
        record.stage = "test"
        record.started = "2024-01-01T00:00:00Z"
        record.command = ["test"]
        record.function_ids = None
        record.input_files = None
        record.output_files = None
        record.summary = None
        record.metadata = None
        record.opencode_log_path = None
        record.opencode_trace_path = None

        # Patch side-effect functions so this runs purely in memory
        orig_record_call = target.record_opencode_call
        orig_utc_now = target.utc_now_iso
        target.record_opencode_call = lambda **kwargs: None
        target.utc_now_iso = lambda: '2024-01-01T00:00:01Z'

        try:
            target.finish_opencode_trace(record)
        finally:
            target.record_opencode_call = orig_record_call
            target.utc_now_iso = orig_utc_now

        passed = not stderr_joined_flag.is_set()

        if passed:
            print('CONFIRMED — stderr_thread was NOT joined before trace event was committed')
        else:
            print('NOT CONFIRMED — stderr_thread was joined before trace event was committed')

    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
