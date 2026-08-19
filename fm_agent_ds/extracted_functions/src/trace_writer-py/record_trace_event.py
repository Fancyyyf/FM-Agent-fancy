def record_trace_event(trace_dir, event):
    if not trace_dir:
        return
    append_event(trace_dir, event)
