# [SPEC]
# Unit: src/domain_knowledge.py
#
# _split_env_paths(value) -> list
#
# Pre-condition:
#   - value is None or a string
#
# Post-condition:
#   - If value is None or empty, returns an empty list
#   - For a non-empty value, the function treats both the OS path separator (os.pathsep) and newline characters as path element separators, producing a list of individual path strings
#   - Every element in the returned list is a non-empty string with no leading or trailing whitespace
#   - The relative order of the returned path elements corresponds to their order of appearance in value
#   - Empty path components (those that become empty after whitespace stripping) are discarded and do not appear in the result
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _split_env_paths(value):
    if not value:
        return []
    normalized = value.replace("\n", os.pathsep)
    return [part.strip() for part in normalized.split(os.pathsep) if part.strip()]
