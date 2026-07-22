# [SPEC]
# Unit: src/pipeline_setup-py/_phases_cover_current_sources.py
#
# _phases_cover_current_sources(phases_json, proj_dir, submodules=None) -> bool
#
# Pre-condition:
#   - phases_json is a string path
#   - proj_dir is an existing directory
#   - submodules is None or an iterable of subdirectory name strings
#
# Post-condition:
#   - Returns True when all of the following hold: (a) phases_json is a readable file
#     whose content parses as valid JSON, (b) the JSON contains at least one source file
#     entry across all phases and modules, (c) every source file path listed in the JSON
#     resolves to an existing file under proj_dir, (d) when submodules is neither None
#     nor an empty iterable, every listed source file path falls under at least one of
#     the specified submodule directories (as determined by _is_under_submodules),
#     and (e) every source file under the project directories scoped by submodules
#     (or under all of proj_dir when submodules is None) appears in the JSON
#   - Returns False when any of (a)-(e) fails
#   - Backslash separators in source file paths within the JSON are treated as forward
#     slashes for path comparison and file existence resolution
#   - The function does not create, modify, delete, or rename any file or directory
# [SPEC]

# [INFO]
# _is_under_submodules(sf, submodules) -> bool
#   Pre-condition: sf is a string path; submodules is a non-empty iterable of
#     subdirectory name strings
#   Post-condition: Returns True when sf contains any string from submodules as a
#     path component; returns False when none of the submodule strings appear in sf
# [SPLIT]
# _collect_project_source_files(proj_dir, submodules) -> set
#   Pre-condition: proj_dir is an existing directory; submodules is None or an
#     iterable of subdirectory name strings
#   Post-condition: Returns a set of relative file paths using "/" separators for
#     all discoverable source files under the directories identified by submodules,
#     or under all of proj_dir when submodules is None
# [INFO]

def _phases_cover_current_sources(phases_json, proj_dir, submodules=None):
    """Return whether phases.json is valid for the current source-file set."""
    try:
        with open(phases_json, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False

    listed = set()
    for phase in data.get("phases", []):
        for module in phase.get("modules", []):
            for source_file in module.get("source_files", []):
                listed.add(source_file.replace("\\", "/"))

    if not listed:
        return False
    if submodules and any(not _is_under_submodules(sf, submodules) for sf in listed):
        return False
    if any(not os.path.exists(os.path.join(proj_dir, sf)) for sf in listed):
        return False
    return _collect_project_source_files(proj_dir, submodules).issubset(listed)
