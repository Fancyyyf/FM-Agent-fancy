# [SPEC]
# Unit: src/languages/erlang-py/_caller_module.py
#
# _caller_module(path: str) -> str
#
# Pre-condition:
#   - path is a string representing a filesystem path (typically an absolute path
#     to a source file)
#
# Post-condition:
#   - Returns the Erlang module name derived from the file's base name by
#     replacing the last occurrence of "." in the base name with "-"
#   - When the base name contains no "." character, returns the base name
#     unchanged
#   - The result is deterministic: identical path strings always produce
#     identical return values
#   - The result depends only on the basename portion of path (the final path
#     component after the last "/" or "\")
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _caller_module(path: str) -> str:
    base = os.path.basename(path)
    dot = base.rfind(".")
    return base[:dot] + "-" + base[dot + 1 :] if dot > 0 else base
