# [SPEC]
# Unit: src/git.py
#
# _git(*args, **kwargs) -> str
#
# Pre-condition:
#   - proj_dir is bound in the enclosing lexical scope to a string path
#   - args consists of individual string tokens forming a valid git subcommand and its arguments
#   - kwargs may contain keyword arguments forwarded to the subprocess execution
#
# Post-condition:
#   - Returns the stdout output of the executed git subcommand with leading and trailing
#     whitespace characters removed
#   - The git subcommand is executed with proj_dir as the effective working directory
#   - If the git subcommand exits with a non-zero status, subprocess.CalledProcessError is
#     raised; the exception carries the command string, the non-zero exit code, and the
#     captured stdout and stderr
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _git(*args, **kwargs):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True, capture_output=True, text=True, **kwargs,
        ).stdout.strip()
