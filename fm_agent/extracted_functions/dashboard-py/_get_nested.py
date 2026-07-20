# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_get_nested.py
#
# _get_nested(d, *keys) -> Optional[Any]
#
# Pre-condition:
#   - d is a dict
#   - keys is a sequence of zero or more hashable values
#
# Post-condition:
#   - When keys is empty, returns d unchanged
#   - Otherwise, for key chain k₁, k₂, ..., kₙ:
#     * Walks the chain via successive dict lookups d[k₁], result[k₂], ...
#       using dict.get for each lookup — a missing key at any step yields
#       None rather than raising KeyError
#     * At each step, the intermediate value must be a dict for iteration
#       to continue. If any intermediate value (including None returned by
#       dict.get for a missing key) is not a dict, returns None immediately
#       and no further keys are examined
#     * Returns the final value when every key is found in the
#       corresponding intermediate dict and every intermediate value is a
#       dict
#   - The input dict d is never mutated by this function
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur
