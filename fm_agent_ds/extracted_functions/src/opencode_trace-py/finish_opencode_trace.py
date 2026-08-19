def finish_opencode_trace(record):
    if record.stdin_thread:
        record.stdin_thread.join()
    if record.log_thread:
        record.log_thread.join()
    status = "error" if record.error or record.proc.returncode != 0 else "success"
    record_opencode_call(
        work_dir=record.work_dir,
        event_id=record.event_id,
        stage=record.stage,
        status=status,
        started=record.started,
        ended=utc_now_iso(),
        command=record.command,
        function_ids=record.function_ids,
        input_files=record.input_files,
        output_files=record.output_files,
        exit_code=record.proc.returncode,
        summary=record.summary,
        error=record.error,
        metadata=record.metadata,
        opencode_log_path=record.opencode_log_path,
        opencode_trace_path=record.opencode_trace_path,
    )
