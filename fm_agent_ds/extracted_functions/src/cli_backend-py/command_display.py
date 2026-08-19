def command_display(command):
    argv = command_argv(command)
    suffix = " <stdin>" if command_stdin(command) is not None else ""
    return shlex.join(argv) + suffix
