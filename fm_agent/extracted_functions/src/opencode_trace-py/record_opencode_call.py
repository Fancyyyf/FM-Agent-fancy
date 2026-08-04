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
