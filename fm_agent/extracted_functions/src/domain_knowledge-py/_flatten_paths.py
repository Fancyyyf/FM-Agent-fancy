# [SPEC]
# Unit: src/domain_knowledge.py
#
# _flatten_paths(values) -> list
#
# Pre-condition:
#   - values is None, or an iterable whose elements are either path-like
#     strings or nested iterables (list or tuple) of path-like strings
#
# Post-condition:
#   - Returns a flat list of all non-empty, non-None path-like strings
#     reachable from values by recursively descending into any nested list or
#     tuple elements
#   - An element that is None or an empty string is excluded from the returned
#     list
#   - An element that is a list or tuple is recursively flattened; all
#     non-empty, non-None strings at any nesting depth are included in the
#     returned list
#   - The returned list preserves the depth-first traversal order of elements
#     encountered during flattening
#   - Returns an empty list when values is None, empty, or contains only
#     None/empty elements after flattening
# [SPEC]

# [INFO]
# _flatten_paths(values) -> list
#   Pre-condition: values is None, an iterable of path-like strings, or an
#     iterable containing nested list/tuple iterables of path-like strings
#   Post-condition: returns a flat list of all non-empty, non-None path-like
#     strings from values with all nesting recursively removed; None and empty
#     string elements are excluded
# [INFO]

def _flatten_paths(values):
    paths = []
    for value in values or []:
        if isinstance(value, (list, tuple)):
            paths.extend(_flatten_paths(value))
        elif value:
            paths.append(value)
    return paths
