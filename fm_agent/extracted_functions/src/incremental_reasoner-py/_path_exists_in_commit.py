# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_path_exists_in_commit.py
#
# _path_exists_in_commit(rel_path) -> bool
#
# Pre-condition:
#   - proj_dir (captured from enclosing scope) is a directory containing a git repository
#   - old_commit_id (captured from enclosing scope) is a commit identifier valid in that repository
#   - rel_path is a non-empty string representing a path relative to the repository root
#
# Post-condition:
#   - Returns True when a blob identified by rel_path exists in the tree of old_commit_id
#   - Returns False when rel_path does not identify any blob in the tree of old_commit_id, or when the git command fails for any reason
#   - Does not read the blob content
#   - Does not modify the repository state or any filesystem entry
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _path_exists_in_commit(rel_path):
        """Return whether rel_path exists at old_commit_id without reading its contents."""
        return subprocess.run(
            ["git", "-C", proj_dir, "cat-file", "-e", f"{old_commit_id}:{rel_path}"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode == 0
