# [SPEC]
# Unit: src/opencode_trace.py
#
# finish_opencode_trace(record: TracedOpenCodeProcess) -> None
#
# Pre-condition:
#   - record is a fully populated TracedOpenCodeProcess with non-null work_dir, event_id, stage, started, command, and proc fields
#   - record.proc has already terminated (its returncode is set)
#
# Post-condition:
#   - If record.stdin_thread is not None, that thread has been joined (it is guaranteed completed before this function returns)
#   - If record.log_thread is not None, that thread has been joined (it is guaranteed completed before this function returns)
#   - A trace event of type "opencode_call" has been recorded in the trace database under record.work_dir
#   - The recorded event's status is "success" if and only if record.error is falsy AND record.proc.returncode == 0; otherwise the status is "error"
#   - The recorded event's end_time is the current UTC time at the moment of recording, formatted as ISO 8601
#   - The recorded event preserves the following fields from record unchanged: event_id, stage, started, command, function_ids, input_files, output_files, summary, error, metadata, opencode_log_path, opencode_trace_path, and exit_code
# [SPEC]

# [INFO]
# utc_now_iso() -> str
#   Pre-condition: none
#   Post-condition: returns the current UTC date-time as an ISO 8601 formatted string
# [SPLIT]
# record_opencode_call(work_dir: str, event_id: str, stage: str, status: str, started: str, ended: str, command: list[str], function_ids: list[str] | None, input_files: list[str] | None, output_files: list[str] | None, exit_code: int, summary: str | None, error: str | None, metadata: dict | None, opencode_log_path: str | None, opencode_trace_path: str | None) -> None
#   Pre-condition: work_dir is a valid writable directory path; event_id is a unique non-empty string; status is one of "success", "error", "mismatch", or "format_error"; started and ended are ISO 8601 timestamps with started <= ended
#   Post-condition: a complete trace event JSON object containing all supplied fields is appended to the trace events JSONL file under work_dir
# [INFO]

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
