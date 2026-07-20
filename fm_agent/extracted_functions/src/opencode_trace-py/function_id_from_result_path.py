# [SPEC]
# Unit: src/opencode_trace.py
#
# function_id_from_result_path(path: str) -> str
#
# Pre-condition:
#   - path is a non-empty string representing a file path
#
# Post-condition:
#   - Returns a fully-qualified function name (FQN) string with path segments joined by "::"
#   - The returned FQN contains no file extension: the substring from the last "." (inclusive) onward is removed from the final path segment
#   - If the normalized path (backslashes converted to forward slashes) starts with the literal prefix "fm_agent/logic_verification_results/", that prefix is stripped before deriving the FQN
#   - All remaining path separators ("/") in the stripped, extension-removed path are replaced with "::" to form the FQN
#   - Backslash characters ("\") in the input are treated as equivalent to forward slash ("/") for all path manipulation
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def function_id_from_result_path(path):
    rel = path.replace("\\", "/")
    prefix = "fm_agent/logic_verification_results/"
    if rel.startswith(prefix):
        rel = rel[len(prefix):]
    return os.path.splitext(rel)[0].replace("/", "::")
