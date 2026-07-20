# [SPEC]
# Unit: src/env_check.py
#
# _memory_path(work_dir: str) -> str
#
# Pre-condition:
#   - work_dir is a string referencing an existing directory
#
# Post-condition:
#   - Returns the filesystem path to the persisted memory file within work_dir
#   - The returned path is deterministic: the same work_dir value always produces the same result
#   - The returned path is the concatenation of work_dir, the platform path separator, and the fixed filename ".env_check_memory"
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _memory_path(work_dir):
    return os.path.join(work_dir, ".env_check_memory")
