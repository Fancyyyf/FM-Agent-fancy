# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_strip_star.py
#
# _strip_star(d) -> dict
#
# Pre-condition:
#   - d may be any value; the function gracefully handles non-dict inputs.
#
# Post-condition:
#   - If d is a dict, returns a new dict with the same key-value pairs
#     as d, except that every key whose string representation starts with
#     "*" has that leading "*" character stripped from the key.
#     Keys that do not start with "*" are unchanged.
#   - Every value in the returned dict is the identical object reference
#     as the corresponding value in d (values are not copied or
#     transformed).
#   - The input dict d is not mutated.
#   - If d is not a dict, returns d unchanged.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _strip_star(d):
    """Strip leading '*' from dict keys (lucentia opencode-trace streaming convention)."""
    if not isinstance(d, dict):
        return d
    return {(k[1:] if k.startswith("*") else k): v for k, v in d.items()}
