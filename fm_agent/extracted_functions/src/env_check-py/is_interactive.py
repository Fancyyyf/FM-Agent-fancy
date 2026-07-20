# [SPEC]
# Unit: src/env_check-py/is_interactive.py
#
# is_interactive() -> bool
#
# Pre-condition:
#   - None.
#
# Post-condition:
#   - Returns True when the standard input stream (stdin) is attached to a terminal device,
#     meaning the calling process can receive interactive user input via stdin.
#   - Returns False when stdin is not attached to a terminal (e.g., piped input,
#     redirection from a file, or non-TTY execution environment).
#   - The return value does not depend on any mutable state and is determined solely by
#     the process's file descriptor table at the time of the call.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def is_interactive():
    return sys.stdin.isatty()
