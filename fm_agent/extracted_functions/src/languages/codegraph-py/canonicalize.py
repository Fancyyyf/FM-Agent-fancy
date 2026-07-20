# [SPEC]
# Unit: src/languages/codegraph-py/canonicalize.py
#
# canonicalize(func_name) -> str
#
# Pre-condition:
#   - func_name is a string (may be empty) representing a function name
#     extracted from source code; template angle-bracket parameters must
#     already be stripped by the caller before invoking this function
#
# Post-condition:
#   - Returns func_name unchanged when func_name is empty or contains no
#     characters that conflict with filesystem path names or FQN component
#     separator syntax
#   - Otherwise returns a string where every character in func_name that is
#     invalid in filesystem paths or FQN components is replaced by a
#     deterministic safe substitute character; characters not in the unsafe
#     set are preserved in position
#   - The returned string is safe for use as: an extracted-function filename
#     component, a segment within a "::"-delimited FQN, and a key in call-
#     edge dictionaries
#   - The transformation is deterministic: canonicalize(x) ==
#     canonicalize(x) for all x, and canonicalize(canonicalize(x)) ==
#     canonicalize(x) for all x
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def canonicalize(func_name):
    """Return a filesystem-safe, FQN-safe version of a function name.

    C++ operator overloads like ``operator/`` contain ``/`` which breaks both
    file paths and ``::``-separated FQNs.  This function sanitises those
    characters so the name is safe everywhere it appears: extracted-function
    file names, FQNs, call-edge keys, and scope.py rankings.

    Every entry point that introduces a function name into the system MUST call
    this function before using the name.
    """
    if not func_name:
        return func_name
    for ch in _UNSAFE:
        if ch in func_name:
            return func_name.translate(_SAFE_REPLACE)
    return func_name
