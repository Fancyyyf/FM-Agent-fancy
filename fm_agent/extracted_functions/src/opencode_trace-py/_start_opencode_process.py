def _start_opencode_process(proj_dir, work_dir, event_id, command, trace_log_path):
    stdin_text = command_stdin(command)
    proc = subprocess.Popen(
        command_argv(command),
        cwd=proj_dir,
        env=_opencode_env(work_dir, event_id),
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdin_thread = None
    if stdin_text is not None:
        stdin_thread = threading.Thread(
            target=_write_command_stdin,
            args=(proc.stdin, stdin_text),
            daemon=True,
        )
        stdin_thread.start()
    log_thread = threading.Thread(
        target=_copy_opencode_output,
        args=(proc.stdout, trace_log_path),
        daemon=True,
    )
    log_thread.start()
    return proc, log_thread, stdin_thread
