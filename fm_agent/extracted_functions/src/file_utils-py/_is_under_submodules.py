# [SPEC]
# Unit: src/file_utils.py
#
# _is_under_submodules(rel_path, submodules) -> bool
#
# Pre-condition:
#   - rel_path is a string representing a file or directory path
#   - submodules is None, an empty iterable, or a non-empty iterable of subdirectory
#     name strings, each not containing "/" or "\"
#
# Post-condition:
#   - Returns True when submodules is None or empty, regardless of rel_path value
#   - When submodules is non-empty: normalizes rel_path by replacing every backslash
#     ("\\") with a forward slash ("/") and stripping any leading "./" prefix;
#     returns True if the normalized path is exactly equal to any element of
#     submodules OR if the normalized path begins with any element of submodules
#     followed by "/", and False otherwise
#   - The function performs no filesystem I/O and has no side effects
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _is_under_submodules(rel_path, submodules):
    """Return whether rel_path is inside one of the selected submodule dirs."""
    if not submodules:
        return True
    norm = rel_path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return any(norm == sub or norm.startswith(sub + "/") for sub in submodules)
