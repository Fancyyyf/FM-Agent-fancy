# [SPEC]
# Unit: src/cli_backend.py
#
# command_argv(command) -> list[str]
#
# Pre-condition:
#   - command is one of:
#     a) an object that carries its argument list in an `argv` attribute
#        whose value is a list of strings, or
#     b) a string, or
#     c) an iterable of strings
#
# Post-condition:
#   - When command has an `argv` attribute whose value is a list of strings:
#     returns that list object (the same reference) — it is the caller's
#     responsibility that the returned list contains only strings
#   - When command is a string: returns a new single-element list containing
#     that string
#   - When command is any other iterable of strings: returns a new list whose
#     elements are the strings yielded by iterating over command, preserving
#     iteration order
#   - The returned value is always a list of strings — every element is a str
#   - Returns a list in all cases — no exceptions are raised for any valid
#     input type
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def command_argv(command):
    if isinstance(command, AgentCommand):
        return command.argv
    return list(command)
