def write_payload(trace_dir, event_id, name, content, binary=False):
    payload_dir = _ensure_trace_dirs(trace_dir)
    path = os.path.join(payload_dir, f"{event_id}_{name}")
    tmp_path = path + ".tmp"
    mode = "wb" if binary else "w"
    kwargs = {} if binary else {"encoding": "utf-8"}
    with open(tmp_path, mode, **kwargs) as f:
        f.write(content)
    os.replace(tmp_path, path)
    return os.path.relpath(path, os.path.dirname(trace_dir))
