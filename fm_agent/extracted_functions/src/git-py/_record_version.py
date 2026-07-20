# [SPEC]
# Unit: src/git.py
#
# _record_version(commit_id, work_dir)
#
# Pre-condition:
#   - work_dir is a path to an existing, writable directory
#
# Post-condition:
#   - If commit_id is truthy: the string representation of commit_id followed by a
#     platform-native newline is appended to the file at work_dir/version.log. If
#     that file does not exist, it is created. If work_dir does not exist or is not
#     writable, an OSError is raised by the underlying open() call.
#   - If commit_id is falsy: no file I/O is performed and the filesystem is unchanged.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _record_version(commit_id, work_dir):
    """Append commit_id as a new line to fm_agent/version.log, building up a
    history of processed commits. No-op when commit_id is falsy."""
    if not commit_id:
        return
    version_path = os.path.join(work_dir, "version.log")
    with open(version_path, "a") as f:
        f.write(commit_id + "\n")
