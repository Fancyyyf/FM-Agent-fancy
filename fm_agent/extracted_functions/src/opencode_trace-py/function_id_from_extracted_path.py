# [SPEC]
# Unit: src/opencode_trace.py
#
# function_id_from_extracted_path(path) -> str
#
# Pre-condition:
#   - path is a string containing a file path that may use either "/" or "\\" as path separators
#
# Post-condition:
#   - Returns the fully-qualified function name (FQN) derived from path
#   - If path begins with the prefix "fm_agent/extracted_functions/" or "extracted_functions/" (after normalizing backslashes to "/"), that prefix is removed before deriving the FQN; otherwise the prefix portion of the path is retained as-is
#   - The FQN is formed by: stripping the last file extension (the shortest suffix beginning with the final "." in the filename) from the path, then replacing every remaining "/" separator with "::"
#   - The returned string contains no "/" or "\\" characters and no final file extension
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def function_id_from_extracted_path(path):
    rel = path.replace("\\", "/")
    for prefix in ("fm_agent/extracted_functions/", "extracted_functions/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break
    return os.path.splitext(rel)[0].replace("/", "::")
