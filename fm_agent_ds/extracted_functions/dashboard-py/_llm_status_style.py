def _llm_status_style(code, status):
    text = str(code or status or "?")
    if text == "200" or status in ("success", "mismatch"):
        return "green", "200"
    if status == "format_error" or text.startswith("4") or text == "FMT":
        return "yellow", text
    return "red", text
