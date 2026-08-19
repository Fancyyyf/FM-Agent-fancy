def _ensure_trace_dirs(trace_dir):
    payload_dir = os.path.join(trace_dir, "payloads")
    os.makedirs(payload_dir, exist_ok=True)
    return payload_dir
