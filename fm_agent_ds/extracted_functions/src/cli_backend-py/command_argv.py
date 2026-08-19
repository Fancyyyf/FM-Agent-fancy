def command_argv(command):
    if isinstance(command, AgentCommand):
        return command.argv
    return list(command)
