# [SPEC]
# Unit: src/pipeline_setup-py/_collect_project_source_files.py
#
# _collect_project_source_files(proj_dir, submodules=None) -> set
#
# Pre-condition:
#   - proj_dir is an existing directory
#   - submodules is None or an iterable of subdirectory name strings
#
# Post-condition:
#   - Returns a set of relative file paths using "/" as the separator
#   - Every returned path corresponds to a source file discoverable under one of
#     the directories scoped by submodules, or under all of proj_dir when
#     submodules is None
#   - No returned path identifies a test file
#   - All returned paths are relative to proj_dir
#   - The returned set is empty when no discoverable non-test source files exist
#     under the scoped directories
#   - The function does not create, modify, delete, or rename any file or directory
# [SPEC]

# [INFO]
# _iter_project_source_files(proj_dir, submodules) -> iterable of str
#   Pre-condition: proj_dir is an existing directory; submodules is None or an
#     iterable of subdirectory name strings
#   Post-condition: Yields relative file paths using "/" as the separator for
#     all discoverable source files under the directories scoped by submodules,
#     or under all of proj_dir when submodules is None
# [SPLIT]
# _is_test_file(rel) -> bool
#   Pre-condition: rel is a string representing a relative file path
#   Post-condition: Returns True when rel identifies a test file; returns False
#     otherwise
# [INFO]

def _collect_project_source_files(proj_dir, submodules=None):
    """Return non-test source files currently present in proj_dir, relative to proj_dir."""
    files = set()
    for rel in _iter_project_source_files(proj_dir, submodules):
        if not _is_test_file(rel):
            files.add(rel)
    return files
