# [SPEC]
# Unit: src/languages/erlang-py/_project_fingerprint.py
#
# _project_fingerprint(proj_dir: str) -> tuple
#
# Pre-condition:
#   - proj_dir is a string identifying a filesystem path to an accessible directory
#
# Post-condition:
#   - Returns a 2-tuple (tool_config, file_records)
#   - tool_config captures the ELP tool invocation configuration; it is identical
#     across calls with the same ELP environment and differs when the configuration
#     changes
#   - file_records is a tuple of (relative_path, file_size_bytes, modification_time_ns)
#     entries, one per file under proj_dir that constitutes Erlang project content —
#     Erlang source files, Erlang header files, and project-level build configuration
#     files that exist at the project root — and no files outside that set
#   - Each relative_path is relative to the project root, using the OS path separator
#   - No file path appears more than once in file_records
#   - file_records entries are sorted lexicographically by relative_path
#   - The returned fingerprint is deterministic: given unchanged ELP configuration,
#     unchanged set of Erlang project files, and unchanged size and modification time
#     for every such file, repeated calls return a value that compares equal to prior
#     results
#   - The fingerprint changes if and only if any of the following change: the ELP
#     tool configuration, the set of Erlang project files under proj_dir, or the
#     size or modification time of any Erlang project file
# [SPEC]

# [INFO]
# _iter_project_files(root: str, extensions: set[str]) -> Iterator[str]
#   Pre-condition: root is a path to an accessible directory; extensions is a
#     non-empty set of file extension strings
#   Post-condition: Yields the absolute path of every file under root whose
#     extension is a member of extensions; each yielded path identifies an
#     accessible file whose extension matches one of the given extensions
# [SPLIT]
# _elp_argv() -> tuple
#   Pre-condition: none
#   Post-condition: Returns a tuple of strings capturing the ELP tool invocation
#     configuration; the returned value is identical across calls within the
#     same ELP environment and differs when the ELP environment changes
# [INFO]

def _project_fingerprint(proj_dir: str) -> tuple:
    root = os.path.abspath(proj_dir)
    paths = list(_iter_project_files(root, {".erl", ".hrl"}))
    paths.extend(
        os.path.join(root, name)
        for name in _PROJECT_CONFIG_FILES
        if os.path.isfile(os.path.join(root, name))
    )
    records = []
    for path in sorted(set(paths)):
        stat = os.stat(path)
        records.append((os.path.relpath(path, root), stat.st_size, stat.st_mtime_ns))
    return (tuple(_elp_argv()), tuple(records))
