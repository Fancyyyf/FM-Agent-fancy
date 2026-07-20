# [SPEC]
# Unit: src/opencode_trace.py
#
# _trace_dir(work_dir) -> str
#
# Pre-condition:
#   - work_dir is a filesystem path string
#
# Post-condition:
#   - Returns the filesystem path to the trace data subdirectory under
#     work_dir, formed by joining work_dir with the literal directory
#     name "trace" using the OS path separator
#   - The returned path is deterministically derived from work_dir alone:
#     for a fixed work_dir value, every call returns the identical path
#   - The directory at the returned path may or may not exist on the
#     filesystem; this function does not perform any filesystem I/O
#   - Returns a str in all cases
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _trace_dir(work_dir):
    return os.path.join(work_dir, "trace")
