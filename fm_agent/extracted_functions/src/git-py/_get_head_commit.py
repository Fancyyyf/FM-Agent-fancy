# [SPEC]
# Unit: src/git-py/_get_head_commit.py
#
# _get_head_commit(proj_dir) -> Optional[str]
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path.
#
# Post-condition:
#   - If proj_dir refers to a git repository whose HEAD commit is resolvable, returns
#     the full SHA-1 hash of HEAD as a non-empty stripped string.
#   - If proj_dir is not a git repository or does not have a resolvable HEAD commit,
#     returns None.
#   - The function does not raise exceptions to its callers; all failures are
#     expressed via a None return.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _get_head_commit(proj_dir):
    """Return the latest git commit id of proj_dir, or None if not a git repo."""
    try:
        return subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        logging.info("_get_head_commit: %s is not a git repo.", proj_dir)
        return None
