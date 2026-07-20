# [SPEC]
# Unit: src/env_check-py/_load_ignored.py
#
# _load_ignored(work_dir: str) -> set[str]
#
# Pre-condition:
#   - work_dir is a directory path that exists.
#
# Post-condition:
#   - Returns a set of non-empty strings representing check IDs previously persisted
#     by _save_ignored within the same work_dir.
#   - Returns an empty set when no memory file exists at the path derived from work_dir,
#     or when an I/O error occurs while reading the file.
#   - Every element in the returned set has no leading or trailing whitespace.
# [SPEC]

# [INFO]
# _memory_path(work_dir: str) -> str
#   Pre-condition: work_dir is a directory path that exists.
#   Post-condition: Returns the filesystem path to the persisted memory file within work_dir.
#     The path is deterministic: the same work_dir always produces the same result.
# [INFO]

def _load_ignored(work_dir):
    path = _memory_path(work_dir)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except IOError:
            pass
    return set()
