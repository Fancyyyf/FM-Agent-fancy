def _payload_dir(trace_dir):
    path = os.path.join(trace_dir, "payloads")
    os.makedirs(path, exist_ok=True)
    return path
