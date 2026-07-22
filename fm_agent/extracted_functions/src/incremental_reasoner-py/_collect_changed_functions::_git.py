    def _git(*args):
        return subprocess.run(
            ["git", "-C", proj_dir, *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
