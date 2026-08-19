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
