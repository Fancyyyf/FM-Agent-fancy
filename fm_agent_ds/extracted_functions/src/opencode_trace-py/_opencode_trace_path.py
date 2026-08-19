def _opencode_trace_path(work_dir, event_id):
    return os.path.join(_trace_dir(work_dir), "opencode", f"{event_id}.jsonl")
