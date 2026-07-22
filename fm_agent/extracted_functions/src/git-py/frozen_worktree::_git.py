# [SPEC]
# Unit: src/git.py
#
# _git(*args, **kwargs) -> str
#
# Pre-condition:
#   - proj_dir is a filesystem path in enclosing scope, pointing to a directory.
#   - *args are zero or more positional string arguments forming the git subcommand
#     and its operands (e.g., "add", "-A").
#   - **kwargs are zero or more keyword arguments forwarded to the subprocess
#     invocation, merged with defaults that enforce text-mode output capture and
#     non-zero-exit error raising.
#
# Post-condition:
#   - Executes a git command rooted at proj_dir (equivalent to "git -C proj_dir"
#     followed by each positional argument in order) as a child process.
#   - Neither stdout nor stderr of the child process appears on the parent's
#     standard output or standard error streams.
#   - If the child process terminates with a non-zero exit code, raises
#     subprocess.CalledProcessError whose attributes record the invoked command,
#     the return code, and the captured stdout and stderr strings.
#   - If the child process terminates with exit code zero, returns the captured
#     stdout with every leading and trailing whitespace character (space, tab,
#     newline, carriage return) removed.
#   - The child process inherits the parent process's environment, subject to
#     modification by any env keyword argument passed in **kwargs.
# [SPEC]

# [INFO]
# subprocess.run(args, *, stdin=None, input=None, stdout=None, stderr=None, capture_output=False, shell=False, cwd=None, timeout=None, check=False, encoding=None, errors=None, text=None, env=None, universal_newlines=None, **other_popen_kwargs) -> subprocess.CompletedProcess
#   Pre-condition:
#     - args is a sequence of strings forming a complete command invocation.
#     - When check is True, a non-zero child exit code causes a CalledProcessError
#       to be raised instead of returning a CompletedProcess with a non-zero
#       returncode.
#     - When capture_output is True, stdout and stderr are redirected to internal
#       pipes and are not written to the parent process's file descriptors.
#     - When text is True (or universal_newlines is True), the captured stdout
#       and stderr are decoded from bytes to str using the prevailing locale
#       encoding (or the encoding argument if provided).
#   Post-condition:
#     - Starts the command described by args as a child process and blocks until
#       that process terminates.
#     - Returns a CompletedProcess whose .args, .returncode, .stdout, and
#       .stderr attributes describe the execution.
#     - When check is True and the child process returns a non-zero exit code,
#       raises subprocess.CalledProcessError with .returncode, .cmd, .stdout,
#       and .stderr set from the failed execution.
#     - When check is False or the child process exits zero, .stdout and .stderr
#       are None if not captured, a bytes object if captured without text mode,
#       or a str if captured with text mode.
# [INFO]

    def _git(*args, **kwargs):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True, capture_output=True, text=True, **kwargs,
        ).stdout.strip()
