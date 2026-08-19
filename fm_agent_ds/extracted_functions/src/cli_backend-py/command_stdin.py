def command_stdin(command):
    if isinstance(command, AgentCommand):
        return command.stdin
    return None
