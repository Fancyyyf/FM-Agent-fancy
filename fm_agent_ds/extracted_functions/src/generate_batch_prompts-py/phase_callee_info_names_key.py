def phase_callee_info_names_key(func: dict, phase: int) -> Optional[str]:
    target = f"phase{phase}_callee_info_names_by_caller"
    if target in func:
        return target
    for key in func.keys():
        if key.endswith("_callee_info_names_by_caller") and key.startswith("phase"):
            return key
    return None
