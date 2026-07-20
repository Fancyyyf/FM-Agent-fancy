# [SPEC]
# Unit: src/file_utils.py
#
# _iter_project_source_files(proj_dir, submodules=None) -> Iterator[str]
#
# Pre-condition:
#   - proj_dir is an existing directory path
#   - submodules is None or a non-empty iterable of subdirectory name strings
#
# Post-condition:
#   - Yields zero or more relative file paths using "/" as the path separator
#   - Every yielded path is relative to proj_dir and identifies a regular file under
#     proj_dir whose filename extension matches a pipeline-supported programming language
#   - The traversal excludes directories whose names begin with "." and those whose
#     names belong to a predefined set of well-known directories that contain generated
#     artifacts, dependencies, or tool workspace output rather than project source code
#   - When submodules is None, every qualifying file under the full proj_dir tree
#     (subject to the directory exclusions above) is yielded
#   - When submodules is provided and non-empty, only qualifying files whose
#     project-relative path begins with one of the listed subdirectory name prefixes
#     are yielded
#   - The function does not create, modify, delete, or rename any file or directory
# [SPEC]

# [INFO]
# _is_under_submodules(rel, submodules) -> bool
#   Pre-condition: rel is a project-relative path string using "/" separators;
#     submodules is None or an iterable of subdirectory name strings
#   Post-condition: Returns True when submodules is None; otherwise returns True
#     when the given relative path begins with one of the listed subdirectory name
#     prefixes and False otherwise
# [INFO]

def _iter_project_source_files(proj_dir, submodules=None):
    """Yield project-relative source file paths, optionally limited to submodules."""
    from src.extract import EXT_TO_LANG  # local import to avoid circular import
    source_exts = set(EXT_TO_LANG.keys())
    scan_roots = [proj_dir]
    if submodules:
        scan_roots = [
            os.path.join(proj_dir, submodule.replace("/", os.sep))
            for submodule in submodules
        ]

    for scan_root in scan_roots:
        for root, dirs, files in os.walk(scan_root):
            # Skip hidden dirs and common non-source dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       {'node_modules', '__pycache__', 'venv', '.venv', 'fm_agent'}]
            for fname in files:
                ext = fname.rsplit('.', 1)[-1] if '.' in fname else ''
                if ext not in source_exts:
                    continue
                rel = os.path.relpath(os.path.join(root, fname), proj_dir)
                rel = rel.replace(os.sep, "/")
                if _is_under_submodules(rel, submodules):
                    yield rel
