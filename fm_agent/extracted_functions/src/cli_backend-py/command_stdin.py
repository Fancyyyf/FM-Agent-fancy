# [SPEC]
# Unit: src/cli_backend.py
#
# command_stdin(command) -> str | None
#
# Pre-condition:
#   - command is either an AgentCommand dataclass instance (carrying a
#     stdin attribute whose value is a str or None) or a list of strings
#     representing a bare CLI argument vector without structured metadata
#
# Post-condition:
#   - When command is of a type that carries structured command metadata
#     (specifically AgentCommand, whose dataclass includes a stdin field),
#     returns the value of the stdin field unchanged — a str when stdin
#     content is configured, or None when no stdin is present
#   - When command is of a type that represents only a bare argument list
#     without structured metadata, returns None, indicating that no stdin
#     text is associated with the command
#   - Returns either a str or None in all cases; never raises an exception
#     for any valid command argument
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def command_stdin(command):
    if isinstance(command, AgentCommand):
        return command.stdin
    return None
