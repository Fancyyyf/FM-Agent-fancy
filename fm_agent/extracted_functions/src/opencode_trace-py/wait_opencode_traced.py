# [SPEC]
# Unit: src/opencode_trace.py
#
# wait_opencode_traced(record, timeout_seconds=OPENCODE_TIMEOUT_SECONDS)
#
# Pre-condition:
#   - record is a TracedOpenCodeProcess previously returned by start_opencode_traced.
#   - record.proc refers to a running subprocess that has not yet been waited on.
#   - timeout_seconds is a positive integer; defaults to the configured OPENCODE_TIMEOUT_SECONDS.
#
# Post-condition:
#   - Blocks until one of: the subprocess exits normally, the subprocess is terminated by a signal,
#     or timeout_seconds elapses since invocation of this function.
#   - If timeout_seconds elapses before the subprocess terminates, the subprocess is killed
#     and the post-condition from the resulting forced termination applies.
#   - Returns the subprocess exit code: zero if the process exited with status 0,
#     a positive integer if the process exited with a non-zero status,
#     or the negative of the signal number if the process was terminated by a signal.
#   - If a non-empty error string is produced during waiting, record.error is overwritten with it.
#   - If an empty or None error string is produced during waiting and record.error is None,
#     record.error remains None.
#   - If an empty or None error string is produced during waiting and record.error was already
#     set to a non-None value, the previously set error is preserved.
#   - After return, the subprocess is guaranteed to no longer be running.
# [SPEC]

# [INFO]
# _wait_opencode_process(proc, command, stage, timeout_seconds) -> (int, Optional[str])
#   Pre-condition: proc is a running subprocess.Popen handle; command is the CLI invocation list;
#     stage is a stage name string; timeout_seconds is a positive integer.
#   Post-condition: Blocks until the subprocess exits or timeout_seconds elapses, then returns
#     (exit_code, error_string). exit_code is the process exit code or the negative of the signal
#     number if killed by signal. error_string is None when the exit is clean, or a message
#     describing the failure (including timeout expiration) otherwise.
# [INFO]

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
