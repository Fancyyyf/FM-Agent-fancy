# [SPEC]
# Unit: src/opencode_trace.py
#
# run_opencode_traced(proj_dir, work_dir, command, stage, function_ids=None, input_files=None, output_files=None, summary=None, metadata=None) -> subprocess.CompletedProcess
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory
#   - work_dir is a path to an existing, writable fm_agent workspace directory
#   - command is a non-empty list of strings forming a valid CLI invocation
#   - stage is a non-empty string identifying the pipeline stage
#   - function_ids, when provided, is a list of fully-qualified function name
#     strings
#   - input_files, when provided, is a list of fm_agent-relative input file
#     paths
#   - output_files, when provided, is a list of fm_agent-relative expected
#     output file paths
#   - summary, when provided, is a human-readable description string
#   - metadata, when provided, is a dictionary of arbitrary key-value pairs
#
# Post-condition:
#   - Launches command as a subprocess with work_dir as the working directory
#     and waits for it to complete, subject to a configured timeout
#   - If the subprocess exits with code 0: returns a CompletedProcess
#     containing the command argv and exit code
#   - If the subprocess exits with a non-zero code, or if the configured
#     timeout expires: raises subprocess.CalledProcessError whose returncode
#     reflects the actual exit code (non-zero exit) or a synthetic non-zero
#     code (timeout)
#   - In every exit path — success, non-zero exit, or timeout — writes
#     exactly one structured trace event as a JSON line appended to
#     fm_agent/trace/events.jsonl
#   - The trace event includes the event ID, stage name, start and end
#     timestamps in ISO 8601 UTC, status ("success" for exit code 0,
#     "error" otherwise), the full command, function IDs, input and output
#     file lists, exit code, summary, error description when the outcome is
#     a failure, and metadata
#   - When a failure (non-zero exit or timeout) occurs, the trace event is
#     written before the CalledProcessError propagates, guaranteeing that
#     every invocation is recorded regardless of outcome
#   - All subprocess output-capture background threads are joined before the
#     function returns or raises, ensuring no dangling threads
# [SPEC]

# [INFO]
# new_event_id(prefix) -> str
#   Pre-condition: prefix is a non-empty string
#   Post-condition: returns a globally unique event identifier string
# [SPLIT]
# utc_now_iso() -> str
#   Pre-condition: none
#   Post-condition: returns the current UTC time formatted as an ISO 8601
#     string
# [SPLIT]
# _opencode_log_path(work_dir, event_id) -> str
#   Pre-condition: work_dir is an existing directory path; event_id is a
#     non-empty string
#   Post-condition: returns the file path where the subprocess stdout and
#     stderr log will be written during execution
# [SPLIT]
# _opencode_trace_path(work_dir, event_id) -> str
#   Pre-condition: work_dir is an existing directory path; event_id is a
#     non-empty string
#   Post-condition: returns the file path where the raw LLM request/response
#     trace will be written
# [SPLIT]
# _start_opencode_process(proj_dir, work_dir, event_id, command, opencode_log_path) -> (Popen, Thread | None, Thread | None)
#   Pre-condition: proj_dir and work_dir are existing directory paths;
#     command is a non-empty argument list; event_id identifies a unique
#     trace event; opencode_log_path is a writable file path
#   Post-condition: launches the subprocess and starts background threads
#     for log capture and optional stdin; returns the process handle and
#     both thread handles (thread handles may be None if no thread was
#     started)
# [SPLIT]
# _wait_opencode_process(proc, command, stage) -> (int, str | None)
#   Pre-condition: proc is a running subprocess.Popen handle; command is the
#     argument list that launched it; stage is the pipeline stage name
#   Post-condition: blocks until the subprocess completes or the configured
#     timeout expires; returns a tuple (exit_code, error_string) where
#     error_string is None on clean completion and non-empty when the
#     subprocess times out or fails
# [SPLIT]
# command_argv(command) -> list[str]
#   Pre-condition: command is either a list of strings or an object with an
#     argv attribute that is a list of strings
#   Post-condition: returns the argument list converted to a plain list of
#     strings
# [SPLIT]
# record_opencode_call(...) -> None
#   Pre-condition: work_dir is a writable directory; event_id is a unique
#     string; all provided fields match their expected types
#   Post-condition: appends a complete trace event as a JSON line to
#     fm_agent/trace/events.jsonl and returns with no value
# [INFO]

def run_opencode_traced(
    proj_dir,
    work_dir,
    command,
    stage,
    function_ids=None,
    input_files=None,
    output_files=None,
    summary=None,
    metadata=None,
):
    event_id = new_event_id("opencode")
    started = utc_now_iso()
    exit_code = 0
    error = None
    opencode_log_path = _opencode_log_path(work_dir, event_id)
    opencode_trace_path = _opencode_trace_path(work_dir, event_id)
    log_thread = None
    stdin_thread = None
    try:
        proc, log_thread, stdin_thread = _start_opencode_process(proj_dir, work_dir, event_id, command, opencode_log_path)
        exit_code, error = _wait_opencode_process(proc, command, stage)
        if error:
            raise subprocess.CalledProcessError(exit_code, command_argv(command))
        if log_thread:
            log_thread.join()
        if stdin_thread:
            stdin_thread.join()
        if exit_code != 0:
            raise subprocess.CalledProcessError(exit_code, command_argv(command))
        return subprocess.CompletedProcess(command_argv(command), exit_code)
    except subprocess.CalledProcessError as exc:
        exit_code = exc.returncode
        error = error or str(exc)
        raise
    finally:
        if log_thread and log_thread.is_alive():
            log_thread.join()
        if stdin_thread and stdin_thread.is_alive():
            stdin_thread.join()
        record_opencode_call(
            work_dir=work_dir,
            event_id=event_id,
            stage=stage,
            status="success" if exit_code == 0 else "error",
            started=started,
            ended=utc_now_iso(),
            command=command,
            function_ids=function_ids,
            input_files=input_files,
            output_files=output_files,
            exit_code=exit_code,
            summary=summary,
            error=error,
            metadata=metadata,
            opencode_log_path=opencode_log_path,
            opencode_trace_path=opencode_trace_path,
        )
