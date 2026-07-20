# [SPEC]
# Unit: src/opencode_trace.py
#
# _opencode_log_path(work_dir, event_id) -> str
#
# Pre-condition:
#   - work_dir is a path to an existing directory
#   - event_id is a non-empty string
#
# Post-condition:
#   - Returns a filesystem path under work_dir that is deterministically
#     derived from work_dir and event_id alone
#   - The returned path identifies the file where the subprocess stdout
#     and stderr log output associated with event_id will be written
#     during execution
#   - For a fixed (work_dir, event_id) pair, every call to this function
#     returns the same path
# [SPEC]

# [INFO]
# _trace_dir(work_dir) -> str
#   Pre-condition: work_dir is a path to an existing directory
#   Post-condition: returns the path to a subdirectory under work_dir
#     dedicated to storing execution trace data
# [SPLIT]
# _payload_dir(trace_dir) -> str
#   Pre-condition: trace_dir is a path to an execution trace directory
#   Post-condition: returns the path to a subdirectory under trace_dir
#     dedicated to storing trace event payload files
# [INFO]

def _opencode_log_path(work_dir, event_id):
    return os.path.join(_payload_dir(_trace_dir(work_dir)), f"{event_id}_opencode.log")
