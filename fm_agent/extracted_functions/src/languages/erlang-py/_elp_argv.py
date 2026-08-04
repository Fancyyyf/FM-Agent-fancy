def _elp_argv() -> list[str]:
    command = settings.erlang.command.strip() or "elp"
    argv = shlex.split(command, posix=os.name != "nt")
    if not argv:
        argv = ["elp"]
    return [*argv, "server"]
