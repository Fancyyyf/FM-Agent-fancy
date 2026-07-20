# [SPEC]
# Unit: src/opencode_trace.py
#
# _wait_opencode_process(proc, command, stage, timeout_seconds=OPENCODE_TIMEOUT_SECONDS) -> (int, str | None)
#
# Pre-condition:
#   - proc is a running subprocess.Popen handle that has not yet been waited on
#   - command is the list of strings that was used to launch proc
#   - stage is a non-empty string identifying the pipeline stage
#   - timeout_seconds is a positive integer; defaults to the configured
#     OPENCODE_TIMEOUT_SECONDS
#
# Post-condition:
#   - Blocks until one of: the subprocess exits normally, or timeout_seconds
#     elapses since invocation of this function
#   - If the subprocess exits within the timeout: returns (exit_code, None)
#     where exit_code is the process exit code — 0 for success, a positive
#     integer for a non-zero exit
#   - If timeout_seconds elapses before the subprocess exits: sends SIGTERM to
#     the subprocess, waits for termination, and if the subprocess has still
#     not terminated after a grace period sends SIGKILL and waits again
#   - If the subprocess is forcibly terminated due to timeout and its final
#     exit code is zero or falsy, the returned exit code is -15, guaranteeing
#     that a timeout is never recorded as success
#   - If the subprocess is killed by a signal during the timeout handling, the
#     returned exit code is the negative of the signal number
#   - When a timeout occurs, returns a non-None error string describing the
#     timeout; when no timeout occurs, the error component is None
#   - After return, the subprocess is guaranteed to no longer be running
# [SPEC]

# [INFO]
# command_display(command) -> str
#   Pre-condition: command is a list of strings forming a CLI invocation
#   Post-condition: returns a human-readable string representation of the
#     command, suitable for diagnostic and log messages
# [INFO]

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
