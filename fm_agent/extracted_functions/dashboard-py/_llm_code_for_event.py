# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_llm_code_for_event.py
#
# _llm_code_for_event(status) -> str
#
# Pre-condition:
#   - status is a string or None, representing the "status" field of a
#     trace event (e.g., "success", "error", "mismatch", "format_error")
#
# Post-condition:
#   - Returns a non-empty string that classifies status into a fixed set
#     of category codes.
#   - Every recognized status string maps deterministically to a single
#     category code: statuses indicating a completed operation (whether
#     the result matched or not) map to a numeric success code; each
#     distinct failure-type status maps to a distinct short non-numeric
#     code.
#   - When status is not among the recognized classification set but is
#     truthy, the status value itself is returned unchanged.
#   - When status is falsy (empty string or None), "?" is returned.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _llm_code_for_event(status):
    if status in ("success", "mismatch"):
        return "200"
    if status == "format_error":
        return "FMT"
    if status == "error":
        return "ERR"
    return status or "?"
