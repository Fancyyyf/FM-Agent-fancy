# [SPEC]
# Unit: src/generate_batch_prompts-py/phase_callers_key.py
#
# phase_callers_key(func, phase) -> str
#
# Pre-condition:
#   - func is a dict representing a function entry from a topdown-layer definition
#   - phase is a non-negative integer
#
# Post-condition:
#   - Returns a string that can be used as a dictionary key to access the set of in-phase caller FQNs stored in func
#   - When func contains a key exactly equal to "phase<N>_callers" where N is the value of phase, returns that key
#   - When func lacks the exact phase-specific key but contains at least one key whose name starts with "phase" and ends with "_callers", returns a key from func matching that pattern
#   - When func contains no key matching either condition, returns the computed target string "phase<N>_callers" where N is the value of phase
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def phase_callers_key(func: dict, phase: int) -> str:
    target = f"phase{phase}_callers"
    if target in func:
        return target
    for key in func.keys():
        if key.endswith("_callers") and key.startswith("phase"):
            return key
    return target
