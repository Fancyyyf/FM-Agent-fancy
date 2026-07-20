# [SPEC]
# Unit: src/git-py/_is_git_repo.py
#
# _is_git_repo(proj_dir) -> bool
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path.
#
# Post-condition:
#   - Returns True if and only if proj_dir is a git repository with a resolvable
#     HEAD commit (the directory is recognized by git as a repository and contains
#     at least one commit).
#   - Returns False if proj_dir is not a git repository or is a git repository
#     with no commits.
#   - The function does not raise exceptions to its callers; all outcomes are
#     expressed via the boolean return value.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _is_git_repo(proj_dir):
    """Return whether proj_dir is a git repository with at least one commit."""
    try:
        subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
