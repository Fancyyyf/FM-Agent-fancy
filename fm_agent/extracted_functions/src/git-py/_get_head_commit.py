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
