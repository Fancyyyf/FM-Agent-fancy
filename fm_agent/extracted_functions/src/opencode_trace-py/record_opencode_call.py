# [SPEC]
# Unit: src/opencode_trace.py
#
# record_opencode_call(work_dir, event_id, stage, status, started, ended, command, function_ids, input_files, output_files, exit_code, summary, error, metadata, opencode_log_path, opencode_trace_path) -> None
#
# Pre-condition:
#   - work_dir is a valid writable directory path
#   - event_id is a unique, non-empty string
#   - stage is a non-empty string identifying the pipeline stage
#   - status is one of "success", "error", "mismatch", or "format_error"
#   - started and ended are ISO 8601 UTC timestamp strings with started <= ended
#   - command is a list of strings forming a valid CLI invocation
#   - function_ids, when not None, is a list of fully-qualified function name strings
#   - input_files, when not None, is a list of file path strings
#   - output_files, when not None, is a list of file path strings
#   - exit_code, when not None, is an integer process exit code
#   - summary, when not None, is a human-readable description string
#   - error, when not None, is an error description string
#   - metadata, when not None, is a dictionary of key-value pairs
#   - opencode_log_path, when not None, is a filesystem path
#   - opencode_trace_path, when not None, is a filesystem path
#
# Post-condition:
#   - Appends exactly one trace event of type "opencode_call" as a single JSON line to the
#     trace events file under work_dir (specifically trace/events.jsonl within work_dir)
#   - The recorded event's event_id, stage, status, start_time, end_time reflect the
#     corresponding parameter values unchanged
#   - The recorded event's function_ids is the provided list when non-None, or an empty list
#     when None
#   - The recorded event's summary is the provided value when non-None, or a default string
#     of the form "OpenCode <stage>" when None
#   - When opencode_log_path is provided and the file it refers to actually exists on disk,
#     the event includes a child payload entry of type "tool_output" labeled "opencode-stdout",
#     referencing the file via a path relative to the trace directory; when the file does not
#     exist or opencode_log_path is None, no such child entry is included
#   - When opencode_trace_path is provided and the file it refers to actually exists on disk,
#     the event includes a child payload entry of type "tool_output" labeled "opencode-llm-jsonl",
#     referencing the file via a path relative to the trace directory; when the file does not
#     exist or opencode_trace_path is None, no such child entry is included
#   - The event's metadata block merges: the full argv of command, exit_code, input_files
#     (empty list when None), output_files (empty list when None), error, a display-formatted
#     command string, and every key-value pair from the provided metadata dict (when not None)
#   - Returns None — all effects are side effects on the trace events file
# [SPEC]

# [INFO]
# _trace_dir(work_dir) -> str
#   Pre-condition: work_dir is a valid directory path
#   Post-condition: returns the trace subdirectory path under work_dir as an absolute path
# [SPLIT]
# _payload_ref(trace_dir, source_path) -> str
#   Pre-condition: trace_dir is a valid directory path; source_path is a filesystem path
#   Post-condition: returns a relative path from trace_dir to source_path, suitable as a
#     content reference in a trace event payload
# [SPLIT]
# command_argv(command) -> list[str]
#   Pre-condition: command is a list of strings or a string
#   Post-condition: returns command as a list of strings, normalizing a single string to a
#     single-element list if needed
# [SPLIT]
# command_display(command) -> str
#   Pre-condition: command is a list of strings forming a CLI invocation
#   Post-condition: returns a human-readable shell-quoted representation of command suitable
#     for display in trace metadata
# [SPLIT]
# record_trace_event(trace_dir, event_dict) -> None
#   Pre-condition: trace_dir is a valid, writable directory; event_dict is a JSON-serializable
#     dict containing at least event_id, type, stage, status, start_time, and end_time
#   Post-condition: serializes event_dict as a single JSON line and appends it to
#     trace/events.jsonl within trace_dir, creating the file and parent directories if they
#     do not exist; returns None
# [INFO]

def record_opencode_call(
    work_dir,
    event_id,
    stage,
    status,
    started,
    ended,
    command,
    function_ids=None,
    input_files=None,
    output_files=None,
    exit_code=None,
    summary=None,
    error=None,
    metadata=None,
    opencode_log_path=None,
    opencode_trace_path=None,
):
    trace_dir = _trace_dir(work_dir)
    children = []

    if opencode_log_path and os.path.exists(opencode_log_path):
        opencode_log_ref = _payload_ref(trace_dir, opencode_log_path)
        children.append(
            {
                "type": "tool_output",
                "label": "opencode-stdout",
                "path": opencode_log_ref,
                "content_ref": opencode_log_ref,
            }
        )
    if opencode_trace_path and os.path.exists(opencode_trace_path):
        opencode_trace_ref = _payload_ref(trace_dir, opencode_trace_path)
        children.append(
            {
                "type": "tool_output",
                "label": "opencode-llm-jsonl",
                "path": opencode_trace_ref,
                "content_ref": opencode_trace_ref,
            }
        )
    record_trace_event(trace_dir, {
        "event_id": event_id,
        "type": "opencode_call",
        "stage": stage,
        "status": status,
        "start_time": started,
        "end_time": ended,
        "summary": summary or f"OpenCode {stage}",
        "function_ids": function_ids or [],
        "children": children,
        "metadata": {
            "command": command_argv(command),
            "exit_code": exit_code,
            "input_files": input_files or [],
            "output_files": output_files or [],
            "error": error,
            **(metadata or {}),
            "command_display": command_display(command),
        },
    })
