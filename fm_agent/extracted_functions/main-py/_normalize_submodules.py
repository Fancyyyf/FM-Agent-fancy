# [SPEC]
# Unit: main.py
#
# _normalize_submodules(proj_dir, submodules) -> list[str]
#
# Pre-condition:
#   - proj_dir is a string representing an existing project root directory path
#   - submodules is None, an empty iterable, or an iterable of strings, each a relative or absolute path
#
# Post-condition:
#   - Returns a list of project-relative directory paths using "/" as the path separator, regardless of platform
#   - Each returned path is a valid existing subdirectory strictly inside proj_dir (not proj_dir itself)
#   - No returned path is a descendant of any other returned path: the result is a minimal covering set of the input submodules
#   - The list contains no duplicate entries
#   - The list is ordered by increasing path depth (number of "/" characters), with paths of equal depth ordered lexicographically
#   - If submodules is None or contains only empty/whitespace-only strings, returns an empty list
#   - Raises ValueError if any input path resolves outside proj_dir
#   - Raises ValueError if any input path resolves to proj_dir itself
#   - Raises ValueError if any input path does not correspond to an existing directory
# [SPEC]

# [INFO]
# _is_under_submodules(rel, collapsed) -> bool
#   Pre-condition: rel is a relative path string using "/" separators; collapsed is a list of relative path strings using "/" separators
#   Post-condition: Returns True when rel, interpreted as a directory hierarchy, has a path prefix that equals one of the paths in collapsed; returns False otherwise
# [INFO]

def _normalize_submodules(proj_dir, submodules):
    """Return validated project-relative submodule directories."""
    if not submodules:
        return []

    proj_dir = os.path.abspath(proj_dir)
    normalized = []
    seen = set()
    for raw in submodules:
        value = (raw or "").strip()
        if not value:
            continue
        candidate = value if os.path.isabs(value) else os.path.join(proj_dir, value)
        candidate = os.path.abspath(candidate)
        try:
            inside_project = os.path.commonpath([proj_dir, candidate]) == proj_dir
        except ValueError:
            inside_project = False
        if not inside_project or candidate == proj_dir:
            raise ValueError(
                f"--submodule must name subdirectories inside proj_dir, got: {raw}"
            )
        if not os.path.isdir(candidate):
            raise ValueError(f"--submodule path is not a directory: {raw}")

        rel = os.path.relpath(candidate, proj_dir).replace(os.sep, "/")
        if rel not in seen:
            normalized.append(rel)
            seen.add(rel)

    collapsed = []
    for rel in sorted(normalized, key=lambda path: (path.count("/"), path)):
        if not collapsed or not _is_under_submodules(rel, collapsed):
            collapsed.append(rel)
    return collapsed
