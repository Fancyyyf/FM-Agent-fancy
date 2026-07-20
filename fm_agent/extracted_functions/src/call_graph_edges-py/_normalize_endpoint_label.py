# [SPEC]
# Unit: src/call_graph_edges.py
#
# _normalize_endpoint_label(label: str) -> str
#
# Pre-condition:
#   - label is a non-empty string
#
# Post-condition:
#   - Returns a string
#   - When the input label represents a function reference qualified by a source-file
#     path, the returned FQN has the source-file extension dot in the filename
#     replaced with "-", leading "./" stripped, "." and empty parent-directory
#     components excluded, and components joined with "::"
#   - When the input label does not represent a path-qualified function reference,
#     the returned string equals the input
#   - The normalization is deterministic: the same input always produces the same
#     output
# [SPEC]

# [INFO]
# _clean_label(label: str) -> str
#   Pre-condition: label is a non-empty string
#   Post-condition: Returns a string whose path-vs-non-path classification and
#     function-name suffix are preserved; the transformation is deterministic and
#     identity-preserving for function references
# [SPLIT]
# _is_path_function_label(label: str) -> bool
#   Pre-condition: label is a cleaned label string
#   Post-condition: Returns True when the label contains a source-file path prefix
#     whose filename extension dot must be replaced with "-" for FQN normalization;
#     returns False otherwise; the classification is deterministic
# [INFO]

def _normalize_endpoint_label(label: str) -> str:
    label = _clean_label(label)
    if _is_path_function_label(label):
        path, func = label.rsplit("::", 1)
        path = path.lstrip("./")
        src_path = PurePosixPath(path)
        base = src_path.name
        last_dot = base.rfind(".")
        func_dir = base[:last_dot] + "-" + base[last_dot + 1:] if last_dot > 0 else base
        parts = [p for p in src_path.parent.parts if p not in {"", "."}]
        return "::".join([*parts, func_dir, func])
    return label
