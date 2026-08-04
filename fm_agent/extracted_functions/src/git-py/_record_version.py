def _record_version(commit_id, work_dir):
    """Append commit_id as a new line to fm_agent/version.log, building up a
    history of processed commits. No-op when commit_id is falsy."""
    if not commit_id:
        return
    version_path = os.path.join(work_dir, "version.log")
    with open(version_path, "a") as f:
        f.write(commit_id + "\n")
