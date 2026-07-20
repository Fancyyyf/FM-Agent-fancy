# [SPEC]
# Unit: src/call_graph_edges.py
#
# _is_path_function_label(label: str) -> bool
#
# Pre-condition:
#   - label is a string
#
# Post-condition:
#   - Returns a boolean
#   - Returns True when label contains "::" AND the substring before the last "::"
#     contains "/" AND the final POSIX-path component of that substring contains "."
#   - Returns False in all other cases, including when label is empty or does not
#     contain "::"
#   - The classification is deterministic: the same input always produces the same
#     output
#   - Never raises an exception on any input
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _is_path_function_label(label: str) -> bool:
    if "::" not in label:
        return False
    path, _func = label.rsplit("::", 1)
    return "/" in path and "." in PurePosixPath(path).name
