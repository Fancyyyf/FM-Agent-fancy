# [SPEC]
# Unit: src/incremental_reasoner-py/_is_workspace_file.py
#
# _is_workspace_file(rel_path) -> bool
#
# Pre-condition:
#   - rel_path is a string representing a file path that may use '/' or '\' separators
#
# Post-condition:
#   - Returns True when rel_path, after normalizing all path separators to '/', equals
#     exactly "fm_agent" or begins with "fm_agent/"
#   - Returns False for all other paths, including paths that contain "fm_agent" as a
#     substring that is not a leading path component (e.g., "src/fm_agent_utils/file.py")
#   - The result is independent of whether the input uses '\' or '/' as the path separator
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _is_workspace_file(rel_path):
        norm = rel_path.replace("\\", "/")
        return norm == "fm_agent" or norm.startswith("fm_agent/")
