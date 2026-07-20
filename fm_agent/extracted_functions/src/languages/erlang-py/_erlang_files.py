# [SPEC]
# Unit: src/languages/erlang-py/_erlang_files.py
#
# _erlang_files(proj_dir: str) -> list[str]
#
# Pre-condition:
#   - proj_dir is a path to an existing directory
#
# Post-condition:
#   - Returns a list of absolute paths to all .erl files found recursively under
#     the directory tree rooted at proj_dir
#   - Returns an empty list when no .erl files exist under proj_dir
#   - The returned list is sorted lexicographically
#   - Every element in the returned list is an absolute path
#   - No path appears more than once in the returned list
# [SPEC]

# [INFO]
# _iter_project_files(dir: str, extensions: set[str]) -> iterable[str]
#   Pre-condition: dir is a path to an existing directory; extensions is a non-empty
#     set of extension strings each including a leading dot
#   Post-condition: Yields absolute paths to all files found recursively under dir
#     whose extension matches one of the members of extensions
# [INFO]

def _erlang_files(proj_dir: str) -> list[str]:
    return sorted(_iter_project_files(proj_dir, {".erl"}))
