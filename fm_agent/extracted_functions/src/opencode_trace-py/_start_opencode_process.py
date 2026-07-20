# [SPEC]
# Unit: src/opencode_trace.py
#
# _start_opencode_process(proj_dir, work_dir, event_id, command, trace_log_path) -> (subprocess.Popen, threading.Thread, threading.Thread | None)
#
# Pre-condition:
#   - proj_dir is a path to an existing directory on the filesystem
#   - work_dir is a path to an existing directory on the filesystem
#   - event_id is a non-empty unique string identifying this trace event
#   - command is an AgentCommand or a non-empty list of strings forming a valid
#     CLI invocation
#   - trace_log_path is a filesystem path under work_dir whose parent
#     directories exist
#
# Post-condition:
#   - Launches command as a subprocess whose working directory is proj_dir,
#     whose environment variables are derived from work_dir and event_id, and
#     whose stdout and stderr are merged into a single pipeline for capture
#   - The subprocess receives input via a connected stdin pipe if and only if
#     the command carries non-None stdin text; otherwise stdin is not connected
#     to the subprocess
#   - The subprocess text stream encoding is UTF-8 with replacement on decode
#     errors, guaranteeing no UnicodeDecodeError on output read
#   - Starts a background daemon thread that copies the subprocess merged output
#     to trace_log_path as it is produced, ensuring every byte written by the
#     subprocess is recorded
#   - If the command carries non-None stdin text, starts a background daemon
#     thread that writes that text to the subprocess stdin pipe and then closes
#     it; if the command carries no stdin text, no stdin-writing thread is
#     started
#   - Returns a tuple of (process_handle, log_thread, stdin_thread) where
#     log_thread is always a started threading.Thread, and stdin_thread is
#     either a started threading.Thread or None
#   - All launched threads are daemon threads: they will not prevent the calling
#     process from exiting
#   - The subprocess has not yet been waited on; its exit code is not available
# [SPEC]

# [INFO]
# command_stdin(command) -> Optional[str]
#   Pre-condition: command is an AgentCommand or list of strings
#   Post-condition: returns the stdin text payload of the command, or None
#     if the command has no stdin text
# [SPLIT]
# command_argv(command) -> list[str]
#   Pre-condition: command is an AgentCommand or list of strings
#   Post-condition: returns the argument list suitable for passing to
#     subprocess.Popen as the command to execute
# [SPLIT]
# _opencode_env(work_dir, event_id) -> dict
#   Pre-condition: work_dir is an existing directory path; event_id is a
#     non-empty string
#   Post-condition: returns a dictionary of environment variables for the
#     subprocess, derived from work_dir and event_id, that is a superset of
#     the current process environment
# [SPLIT]
# _write_command_stdin(pipe, text) -> None
#   Pre-condition: pipe is a writable file-like object connected to a
#     subprocess stdin; text is a string
#   Post-condition: writes text to pipe, flushes, and closes the pipe,
#     after which no further writes to the subprocess stdin are possible
# [SPLIT]
# _copy_opencode_output(stream, path) -> None
#   Pre-condition: stream is a readable text stream producing lines; path
#     is a writable filesystem path
#   Post-condition: reads from stream line by line until the stream is
#     exhausted (EOF), writing each line to the file at path, then flushes
#     and closes the output file
# [INFO]

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
