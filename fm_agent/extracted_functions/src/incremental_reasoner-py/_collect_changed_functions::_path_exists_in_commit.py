    def _path_exists_in_commit(rel_path):
        """Return whether rel_path exists at old_commit_id without reading its contents."""
        return subprocess.run(
            ["git", "-C", proj_dir, "cat-file", "-e", f"{old_commit_id}:{rel_path}"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode == 0
