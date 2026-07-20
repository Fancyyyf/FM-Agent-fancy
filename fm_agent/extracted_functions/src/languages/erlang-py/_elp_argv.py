# [SPEC]
# Unit: src/languages/erlang-py/_elp_argv.py
#
# _elp_argv() -> list[str]
#
# Pre-condition:
#   - The process environment is available for reading
#
# Post-condition:
#   - Returns a non-empty list of strings representing the argument vector used to
#     launch the Erlang Language Platform server subprocess
#   - The last element of the returned list is the string "server"
#   - The returned value is deterministic across calls: given an unchanged value of
#     the ELP_COMMAND environment variable and the same operating-system platform
#     (POSIX vs non-POSIX), repeated calls return the same list
#   - When the ELP_COMMAND environment variable changes, the returned list reflects
#     the new command
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _elp_argv() -> list[str]:
    command = os.environ.get("ELP_COMMAND", "elp").strip() or "elp"
    argv = shlex.split(command, posix=os.name != "nt")
    if not argv:
        argv = ["elp"]
    return [*argv, "server"]
