# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/_iter_project_files.py
#
# _iter_project_files(proj_dir: str, suffixes: set[str]) -> Iterator[str]
#
# Pre-condition:
#   - proj_dir is a string representing a valid filesystem path to an existing, accessible
#     directory
#   - suffixes is a non-empty set of strings, each including a leading dot
#
# Post-condition:
#   - Yields the absolute filesystem path of every regular file found recursively under
#     proj_dir whose filename extension matches a member of suffixes, where the comparison
#     is case-insensitive
#   - Directories whose name matches a member of _SKIP_DIRS (case-insensitive) are excluded
#     from traversal; no file under or within any excluded directory is ever yielded
#   - Every yielded path is an absolute path, resolved by the OS according to the filesystem
#     containing proj_dir
#   - Each path is yielded at most once
#   - Files are yielded in the order produced by a recursive depth-first directory traversal
#     starting from proj_dir
#   - If no regular files under proj_dir have a matching extension, the iterator yields
#     nothing and terminates normally
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _iter_project_files(proj_dir: str, suffixes: set[str]):
    for root, dirs, files in os.walk(proj_dir):
        dirs[:] = [directory for directory in dirs if directory.lower() not in _SKIP_DIRS]
        for filename in files:
            if Path(filename).suffix.lower() in suffixes:
                yield os.path.abspath(os.path.join(root, filename))
