# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_llm_status_style.py
#
# _llm_status_style(code, status) -> (str, str)
#
# Pre-condition:
#   - code is an integer, string, or None, representing an HTTP-style
#     status code from a trace event
#   - status is a string or None, representing the "status" field of a
#     trace event
#
# Post-condition:
#   - Returns a pair (color, label) where color is a Rich-compatible
#     color name and label is a display string.
#   - The label is constructed by selecting the first truthy value from
#     code, status, and the string "?" in that priority order, converted
#     to a string.
#   - When the label is "200" or status is a completion-type status
#     (indicating the operation finished), the pair is ("green", "200").
#   - When status is a format-error type or the label begins with "4" or
#     equals "FMT", the pair is ("yellow", label).
#   - For all other code/status combinations, the pair is ("red", label).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _llm_status_style(code, status):
    text = str(code or status or "?")
    if text == "200" or status in ("success", "mismatch"):
        return "green", "200"
    if status == "format_error" or text.startswith("4") or text == "FMT":
        return "yellow", text
    return "red", text
