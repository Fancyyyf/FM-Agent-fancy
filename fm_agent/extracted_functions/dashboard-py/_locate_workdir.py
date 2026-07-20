# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_locate_workdir.py
#
# _locate_workdir(proj_dir) -> Path
#
# Pre-condition:
#   - proj_dir is a value convertible to a pathlib.Path, referencing a
#     directory that exists on the filesystem
#
# Post-condition:
#   - Returns a Path to the fm_agent workspace directory to monitor for
#     the given project directory
#   - When the resolved absolute path of proj_dir is itself an fm_agent
#     workspace (identified by the presence of trace output data within
#     that directory), returns that resolved path verbatim
#   - Otherwise, returns the resolved absolute path of proj_dir with
#     "fm_agent" appended as a child path component
#   - The caller is responsible for verifying that the returned path
#     exists or for creating any missing parent directories
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _locate_workdir(proj_dir):
    """Resolve which fm_agent workdir to monitor.

    Accepts either:
      - A project root: dashboard looks for <root>/fm_agent/ (the live workspace).
      - A workspace directly (any name like fm_agent.opus_partial_*): detected
        by the presence of a `trace/` subdir, used as-is.
    """
    p = Path(proj_dir).resolve()
    if (p / "trace").is_dir():
        return p
    return p / "fm_agent"
