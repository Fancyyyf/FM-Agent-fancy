# [SPEC]
# Unit: src/opencode_trace.py
#
# _deep_merge(base: dict, overlay: dict) -> dict
#
# Pre-condition:
#   - base is a dict
#   - overlay is a dict
#
# Post-condition:
#   - Returns a new dict. Neither base nor overlay is modified.
#   - The returned dict contains the union of keys from base and overlay.
#   - For each key present in both base and overlay:
#     - If both base[key] and overlay[key] are dicts, the returned value is a dict produced
#       by recursively applying these same merge rules to base[key] and overlay[key].
#     - Otherwise, the returned value is overlay[key].
#   - For each key present only in base, the returned value is equal to base[key].
#   - For each key present only in overlay, the returned value is equal to overlay[key].
# [SPEC]

def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge ``overlay`` into ``base``; ``overlay`` wins on conflicting
    leaves, nested dicts are merged (mirrors OpenCode's own config merge)."""
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
