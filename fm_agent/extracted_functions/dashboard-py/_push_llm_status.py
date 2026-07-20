# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_push_llm_status.py
#
# State._push_llm_status(self, ts, source, label, status, model=None, code=None, detail=None) -> None
#
# Pre-condition:
#   - ts is a datetime or None.
#   - source, label, status, model, code, and detail are strings or
#     None.
#   - self.llm_statuses is a mutable sequence that supports appending
#     and evicts the oldest entry when at a fixed maximum capacity.
#
# Post-condition:
#   - A new record is appended to self.llm_statuses.
#   - The record contains the following fields:
#       * "time": "HH:MM:SS" string formatted from ts when ts is
#         truthy; empty string when ts is falsy.
#       * "source": the given source value.
#       * "label": the given label value, defaulting to "llm_call"
#         when label is falsy.
#       * "status": the given status value, defaulting to "?" when
#         status is falsy.
#       * "model": the given model value.
#       * "code": the given code value, defaulting to the status
#         value when code is falsy; if status is also falsy,
#         defaults to "?".
#       * "detail": the given detail value.
#   - self.llm_statuses never exceeds a fixed maximum length; when the
#     append would exceed the maximum, the oldest entry is evicted.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _push_llm_status(self, ts, source, label, status, model=None, code=None, detail=None):
        when = ts.strftime("%H:%M:%S") if ts else ""
        self.llm_statuses.append(
            {
                "time": when,
                "source": source,
                "label": label or "llm_call",
                "status": status or "?",
                "model": model,
                "code": code or status or "?",
                "detail": detail,
            }
        )
