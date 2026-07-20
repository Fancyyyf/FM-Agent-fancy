# [SPEC]
# Unit: src/generate_batch_prompts-py/phase_callee_info_names_key.py
#
# phase_callee_info_names_key(func, phase) -> Optional[str]
#
# Pre-condition:
#   - func is a dictionary
#   - phase is a non-negative integer
#
# Post-condition:
#   - If func contains a key exactly equal to the string
#     "phase<phase>_callee_info_names_by_caller" (where <phase> is the decimal
#     representation of the phase argument), returns that exact key string
#   - Otherwise, if func contains any key that starts with "phase" and ends with
#     "_callee_info_names_by_caller", returns that key string
#   - Otherwise, returns None
#   - The return value is either a string that is an actual key present in func,
#     or None
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def phase_callee_info_names_key(func: dict, phase: int) -> Optional[str]:
    target = f"phase{phase}_callee_info_names_by_caller"
    if target in func:
        return target
    for key in func.keys():
        if key.endswith("_callee_info_names_by_caller") and key.startswith("phase"):
            return key
    return None
