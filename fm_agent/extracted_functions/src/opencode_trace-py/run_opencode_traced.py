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
