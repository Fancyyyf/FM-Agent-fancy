def _llm_code_for_event(status):
    if status in ("success", "mismatch"):
        return "200"
    if status == "format_error":
        return "FMT"
    if status == "error":
        return "ERR"
    return status or "?"
