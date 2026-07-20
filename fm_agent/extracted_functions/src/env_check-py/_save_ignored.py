# [SPEC]
# Unit: src/env_check-py/_save_ignored.py
#
# _save_ignored(work_dir: str, ignored: set[str]) -> None
#
# Pre-condition:
#   - work_dir is a directory path that exists.
#   - ignored is a set of non-empty strings representing check IDs to persist.
#
# Post-condition:
#   - Persists the given set of check IDs to the memory file at the path derived
#     from work_dir, such that a subsequent call to _load_ignored(work_dir) returns
#     a set containing exactly the same elements.
#   - The persisted file contains one check ID per line, in lexicographic order.
#   - Any previously persisted content at the same path is overwritten.
# [SPEC]

# [INFO]
# _memory_path(work_dir: str) -> str
#   Pre-condition: work_dir is a directory path that exists.
#   Post-condition: Returns the filesystem path to the persisted memory file within work_dir.
#     The path is deterministic: the same work_dir always produces the same result.
# [INFO]

def _save_ignored(work_dir, ignored):
    path = _memory_path(work_dir)
    with open(path, "w") as f:
        for item in sorted(ignored):
            f.write(item + "\n")
