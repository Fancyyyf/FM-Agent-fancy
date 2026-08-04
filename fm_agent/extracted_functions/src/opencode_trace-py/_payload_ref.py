def _payload_ref(trace_dir, path):
    return os.path.relpath(path, os.path.dirname(trace_dir))
