# [SPEC]
# Unit: src/trace_writer-py/record_trace_event.py
#
# record_trace_event(trace_dir, event) -> None
#
# Pre-condition:
#   - trace_dir is either a writable directory path or a falsy value (None or empty string)
#   - event is a JSON-serializable dict
#
# Post-condition:
#   - When trace_dir is falsy, returns immediately with no side effects
#   - When trace_dir is a writable directory, the event dict is serialized as a single
#     JSON line and durably appended to the trace event log under trace_dir, with parent
#     directories created if they do not exist
#   - Returns None — all effects are side effects on the persistent trace event log
# [SPEC]

# [INFO]
# append_event(trace_dir, event) -> None
#   Pre-condition: trace_dir is a writable directory path; event is a JSON-serializable dict
#   Post-condition: serializes event as a single JSON line and durably appends it to the
#     trace event log under trace_dir, creating the file and parent directories if they do
#     not exist; the append is guarded by a global lock for thread safety; returns None
# [INFO]

def record_trace_event(trace_dir, event):
    if not trace_dir:
        return
    append_event(trace_dir, event)
