# [SPEC]
# Unit: src/file_utils.py
#
# _has_source_code(proj_dir, submodules=None) -> bool
#
# Pre-condition:
#   - proj_dir is a directory path.
#   - submodules is None or a non-empty list of subdirectory name strings.
#
# Post-condition:
#   - Returns True when proj_dir (optionally scoped to submodules) contains at least one
#     file whose extension matches a pipeline-supported programming language.
#   - Returns False when no such file exists within the applicable scope, including when
#     proj_dir does not exist, is empty, contains no recognized source files, or when
#     submodules narrows the scope to a subset of the tree that contains no recognized
#     source files.
#   - When submodules is None, the search covers the entire directory tree under proj_dir,
#     excluding directories whose names begin with "." and well-known build/package
#     directories.
#   - When submodules is provided and non-empty, only files whose project-relative path
#     begins with one of the listed subdirectory names are considered.
# [SPEC]

# [INFO]
# _iter_project_source_files(proj_dir, submodules=None) -> Iterator[str]
#   Pre-condition: proj_dir is a directory path; submodules is None or a non-empty list
#     of subdirectory name strings.
#   Post-condition: yields every project-relative file path (using "/" separators) under
#     proj_dir whose extension matches a pipeline-supported language, optionally scoped
#     to the submodules tree(s) when submodules is provided; directories whose names begin
#     with "." and well-known build/package directories are excluded from traversal.
# [INFO]

def _has_source_code(proj_dir, submodules=None):
    """Check whether proj_dir contains at least one source code file."""
    for _ in _iter_project_source_files(proj_dir, submodules):
        return True
    return False
