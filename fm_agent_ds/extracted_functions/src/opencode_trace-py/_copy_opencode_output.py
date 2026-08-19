def _copy_opencode_output(stream, trace_log_path=None):
    trace_log = None
    try:
        if trace_log_path:
            trace_log = open(trace_log_path, "w", encoding="utf-8", errors="replace")
        for chunk in iter(lambda: stream.read(4096), ""):
            if not chunk:
                break
            if trace_log:
                trace_log.write(chunk)
                trace_log.flush()
    finally:
        if trace_log:
            trace_log.close()
    stream.close()
