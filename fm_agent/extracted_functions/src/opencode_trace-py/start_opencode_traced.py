# [SPEC]
# Unit: src/opencode_trace.py
#
# start_opencode_traced(proj_dir, work_dir, command, stage, function_ids=None, input_files=None, output_files=None, summary=None, metadata=None)
#
# Pre-condition:
#   - proj_dir is an absolute path to an existing directory on the filesystem.
#   - work_dir is an absolute path to an existing directory.
#   - command is a non-empty list of strings forming a valid CLI invocation.
#   - stage is a non-empty string identifying a pipeline stage.
#   - function_ids, when provided, is a list of fully-qualified function name strings.
#   - input_files, when provided, is a list of fm_agent/-relative file paths.
#   - output_files, when provided, is a list of fm_agent/-relative file paths.
#
# Post-condition:
#   - Returns a TracedOpenCodeProcess whose fields are populated from the corresponding arguments
#     and generated startup values.
#   - The returned record has a globally unique event_id string generated with prefix "opencode_".
#   - The returned record's started field is a UTC timestamp in ISO 8601 format captured at the moment
#     of invocation.
#   - The returned record's proc field refers to a running subprocess whose stdout and stderr streams
#     are being read asynchronously by one or more background threads.
#   - The returned record's opencode_log_path is a filesystem path under work_dir determined solely by
#     work_dir and event_id.
#   - The returned record's opencode_trace_path is a filesystem path under work_dir determined solely by
#     work_dir and event_id.
#   - The returned record's error field is None.
#   - The subprocess has not yet been waited on; its exit code is not available.
#   - Each optional parameter that was passed is stored in the corresponding record field;
#     parameters that were not passed are stored as None in the record.
# [SPEC]

# [INFO]
# new_event_id(prefix) -> str
#   Pre-condition: prefix is a non-empty string.
#   Post-condition: Returns a globally unique string identifier starting with prefix.
# [SPLIT]
# utc_now_iso() -> str
#   Pre-condition: (none)
#   Post-condition: Returns the current UTC date and time formatted as an ISO 8601 string.
# [SPLIT]
# _opencode_log_path(work_dir, event_id) -> str
#   Pre-condition: work_dir is an existing directory path; event_id is a non-empty string.
#   Post-condition: Returns a filesystem path under work_dir that is deterministically derived
#     from work_dir and event_id.
# [SPLIT]
# _opencode_trace_path(work_dir, event_id) -> str
#   Pre-condition: work_dir is an existing directory path; event_id is a non-empty string.
#   Post-condition: Returns a filesystem path under work_dir that is deterministically derived
#     from work_dir and event_id.
# [SPLIT]
# _start_opencode_process(proj_dir, work_dir, event_id, command, opencode_log_path) -> (Popen, Thread, Thread)
#   Pre-condition: proj_dir and work_dir are existing directories; event_id is a unique string;
#     command is a list of strings; opencode_log_path is a valid filesystem path.
#   Post-condition: Returns a tuple of (subprocess handle, log-capture thread, stdin-forwarding thread).
#     The subprocess is running with its stdout and stderr being captured asynchronously.
#     The returned threads are started and actively reading from the subprocess.
# [INFO]

def start_opencode_traced(
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
    opencode_log_path = _opencode_log_path(work_dir, event_id)
    opencode_trace_path = _opencode_trace_path(work_dir, event_id)
    proc, log_thread, stdin_thread = _start_opencode_process(proj_dir, work_dir, event_id, command, opencode_log_path)
    return TracedOpenCodeProcess(
        proc=proc,
        work_dir=work_dir,
        event_id=event_id,
        stage=stage,
        started=started,
        command=command,
        function_ids=function_ids,
        input_files=input_files,
        output_files=output_files,
        summary=summary,
        metadata=metadata,
        opencode_log_path=opencode_log_path,
        opencode_trace_path=opencode_trace_path,
        log_thread=log_thread,
        stdin_thread=stdin_thread,
    )
