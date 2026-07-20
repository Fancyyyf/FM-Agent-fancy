import sys
import os
import subprocess
import tempfile
import shutil

try:
    from src.opencode_trace import finish_opencode_trace, TracedOpenCodeProcess

    # Create a completed subprocess (returncode is set)
    proc = subprocess.Popen(["true"])
    proc.wait()

    # Create a temp directory and make it read-only so os.makedirs
    # cannot create trace/ subdirectories inside it
    work_dir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    os.chmod(work_dir, 0o500)  # r-x------ (no write)

    record = TracedOpenCodeProcess(
        proc=proc,
        work_dir=work_dir,
        event_id="test_event_001",
        stage="spec",
        started="2025-01-01T00:00:00Z",
        command=["opencode", "run", "--stage", "spec"],
        function_ids=["test::func"],
        input_files=[],
        output_files=[],
        summary="test summary",
        metadata={},
        opencode_log_path=None,
        opencode_trace_path=None,
        log_thread=None,
        stdin_thread=None,
        error=None,
    )

    exception_raised = False
    try:
        finish_opencode_trace(record)
    except (FileNotFoundError, OSError, PermissionError):
        exception_raised = True

    # Restore write permission so we can check/clean up
    os.chmod(work_dir, 0o700)

    # Spec says: "A trace event of type opencode_call has been recorded
    # in the trace database under record.work_dir"
    events_path = os.path.join(work_dir, "trace", "events.jsonl")
    trace_recorded = os.path.exists(events_path)

    bug_confirmed = exception_raised and not trace_recorded

    if bug_confirmed:
        print(
            f"CONFIRMED — exception raised: {exception_raised}, "
            f"trace recorded: {trace_recorded} | "
            f"spec requires trace event to be recorded, but "
            f"finish_opencode_trace does not handle exceptions from "
            f"record_opencode_call, so a non-writable work_dir prevents "
            f"recording"
        )
    else:
        print(
            f"NOT CONFIRMED — exception raised: {exception_raised}, "
            f"trace recorded: {trace_recorded}"
        )

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
