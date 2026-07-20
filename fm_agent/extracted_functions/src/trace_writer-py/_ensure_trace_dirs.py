# [SPEC]
# Unit: src/trace_writer-py/_ensure_trace_dirs.py
#
# _ensure_trace_dirs(trace_dir) -> str
#
# Pre-condition:
#   - trace_dir is a string specifying a filesystem path
#
# Post-condition:
#   - The subdirectory named "payloads" under trace_dir exists on the filesystem
#   - Any missing parent directories in the full path to that subdirectory are created as a side effect (the call is idempotent when the directories already exist)
#   - Returns the filesystem path to the "payloads" subdirectory as a string, using the operating-system path separator
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _ensure_trace_dirs(trace_dir):
    payload_dir = os.path.join(trace_dir, "payloads")
    os.makedirs(payload_dir, exist_ok=True)
    return payload_dir
