# [SPEC]
# Unit: src/file_utils.py
#
# _json_file_is_valid(path) -> bool
#
# Pre-condition:
#   - path is a string referencing a filesystem location.
#
# Post-condition:
#   - Returns True if and only if the filesystem object at path is openable
#     for reading and its content is well-formed JSON (parseable by the
#     standard library JSON parser).
#   - Returns False when the filesystem object at path does not exist, cannot
#     be opened for reading, or its content is not well-formed JSON.
#   - Does not raise exceptions to its caller and does not mutate any
#     filesystem state.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _json_file_is_valid(path):
    try:
        with open(path, "r") as f:
            json.load(f)
        return True
    except (OSError, json.JSONDecodeError):
        return False
