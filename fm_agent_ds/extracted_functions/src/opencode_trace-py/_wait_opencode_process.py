def _wait_opencode_process(proc, command, stage, timeout_seconds=OPENCODE_TIMEOUT_SECONDS):
    try:
        return proc.wait(timeout=timeout_seconds), None
    except subprocess.TimeoutExpired:
        # A model connection that dies silently (e.g. through a forward proxy)
        # leaves opencode waiting forever. Kill it so callers' retry paths can
        # take over instead of the whole pipeline hanging.
        logging.warning(
            "opencode %s timed out after %ss, killing: %s",
            stage, timeout_seconds, command_display(command),
        )
        proc.terminate()
        try:
            exit_code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            exit_code = proc.wait()
        if not exit_code:
            exit_code = -15  # killed-on-timeout must never record as success
        return exit_code, f"timeout after {timeout_seconds}s"
