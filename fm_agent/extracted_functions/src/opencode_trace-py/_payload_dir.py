# [SPEC]
# Unit: src/opencode_trace.py
#
# _payload_dir(trace_dir) -> str
#
# Pre-condition:
#   - trace_dir is a path to an existing directory
#
# Post-condition:
#   - Returns a filesystem path identifying a "payloads" subdirectory within trace_dir
#   - After the call returns, the directory at the returned path exists on the filesystem
#   - The directory is the designated storage location for trace event payload files
#   - For a fixed trace_dir, every call to this function returns the same path
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _payload_dir(trace_dir):
    path = os.path.join(trace_dir, "payloads")
    os.makedirs(path, exist_ok=True)
    return path
