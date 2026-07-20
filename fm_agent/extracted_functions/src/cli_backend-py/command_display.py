# [SPEC]
# Unit: src/cli_backend.py
#
# command_display(command) -> str
#
# Pre-condition:
#   - command has a property or attribute that yields a list of strings
#     representing the CLI argv (via command_argv)
#   - command has a property or attribute that yields the stdin text or
#     None (via command_stdin), where None means no stdin is provided
#
# Post-condition:
#   - Returns a single human-readable string representing the full CLI
#     invocation of command, suitable for use in diagnostic messages, log
#     output, and trace metadata
#   - The argv portion of the returned string is shell-quoted such that
#     it can be copied and pasted into a shell to reproduce the invocation
#   - When command has a non-None stdin value, the returned string includes
#     a distinguishable suffix (the substring " <stdin>") appended after
#     the shell-quoted argv, indicating that stdin content is present
#   - When command has a None stdin value, the returned string consists
#     solely of the shell-quoted argv with no additional suffix
#   - Returns a str in all cases — no exceptions are raised for any valid
#     command argument
# [SPEC]

# [INFO]
# command_argv(command) -> list[str]
#   Pre-condition: command is an AgentCommand value with an argv field
#     that is a list of strings
#   Post-condition: returns the argv field of command unchanged
# [SPLIT]
# command_stdin(command) -> str | None
#   Pre-condition: command is an AgentCommand value with a stdin field
#     that is either None or a string
#   Post-condition: returns the stdin field of command unchanged — None
#     when no stdin is configured, the stdin string otherwise
# [INFO]

def command_display(command):
    argv = command_argv(command)
    suffix = " <stdin>" if command_stdin(command) is not None else ""
    return shlex.join(argv) + suffix
