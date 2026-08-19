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
