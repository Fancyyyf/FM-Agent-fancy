# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_git.py
#
# _git(subcommand, *args) -> str
#
# Pre-condition:
#   - subcommand is a valid git subcommand name
#   - args are zero or more string arguments to that subcommand
#   - proj_dir (from enclosing scope) is a directory path containing a git
#     repository cloned from the appropriate remote
#
# Post-condition:
#   - Executes git with -C proj_dir subcommand args using subprocess
#   - Returns the stdout output of the git command as a single string
#   - Raises subprocess.CalledProcessError when the git command exits with
#     a nonzero exit code
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _git(*args):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
