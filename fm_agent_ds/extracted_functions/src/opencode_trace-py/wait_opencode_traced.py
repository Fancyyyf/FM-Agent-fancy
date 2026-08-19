def wait_opencode_traced(record, timeout_seconds=OPENCODE_TIMEOUT_SECONDS):
    exit_code, error = _wait_opencode_process(
        record.proc,
        record.command,
        record.stage,
        timeout_seconds=timeout_seconds,
    )
    if error or record.error is None:
        record.error = error
    return exit_code
