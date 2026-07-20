# [SPEC]
# Unit: src/opencode_trace.py
#
# _payload_ref(trace_dir, path) -> str
#
# Pre-condition:
#   - trace_dir is a valid path to an existing directory
#   - path is a valid filesystem path
#
# Post-condition:
#   - Returns a relative path string from trace_dir to path, resolving to the file
#     or directory identified by path when combined with trace_dir
#   - The returned path is suitable for use as a content reference in a trace event
#     payload
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _payload_ref(trace_dir, path):
    return os.path.relpath(path, os.path.dirname(trace_dir))
