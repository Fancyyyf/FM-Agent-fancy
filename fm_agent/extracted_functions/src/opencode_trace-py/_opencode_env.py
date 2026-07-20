# [SPEC]
# Unit: src/opencode_trace.py
#
# _opencode_env(work_dir, event_id) -> dict
#
# Pre-condition:
#   - work_dir is a path to an existing directory on the filesystem (the fm_agent/
#     workspace directory)
#   - event_id is a non-empty string uniquely identifying a trace event
#
# Post-condition:
#   - Returns a copy of the current process environment (os.environ) with three
#     additional entries: TRACE_DIR, TRACE_FILENAME, and PWD
#   - TRACE_DIR is set to the absolute path of the "opencode" subdirectory under the
#     trace directory derived from work_dir; the directory at TRACE_DIR is created
#     if it does not already exist
#   - TRACE_FILENAME is set to the value of event_id
#   - PWD is set to the absolute path of the parent directory of work_dir (the
#     project root directory)
#   - The returned dictionary contains all entries present in the calling process's
#     environment at the time of the call, preserving their original values except
#     where overwritten by the three entries above
# [SPEC]

# [INFO]
# _trace_dir(work_dir) -> str
#   Pre-condition: work_dir is a filesystem path
#   Post-condition: Returns a path string representing the trace data directory
#     under work_dir
# [INFO]

def _opencode_env(work_dir, event_id):
    env = os.environ.copy()
    trace_dir = os.path.abspath(os.path.join(_trace_dir(work_dir), "opencode"))
    os.makedirs(trace_dir, exist_ok=True)
    env["TRACE_DIR"] = trace_dir
    env["TRACE_FILENAME"] = event_id
    # subprocess.Popen(cwd=...) chdirs the child but doesn't sync PWD; opencode
    # walks PWD upward looking for AGENTS.md, so without this it picks up the
    # fm-agent repo's own AGENTS.md instead of the target's, baking ~10K bytes
    # of repo docs into every system prompt and invalidating the cache prefix
    # on every edit.
    proj_dir = os.path.dirname(os.path.abspath(work_dir))
    env["PWD"] = proj_dir
    return env
