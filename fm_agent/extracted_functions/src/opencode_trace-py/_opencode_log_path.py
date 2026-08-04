def _opencode_log_path(work_dir, event_id):
    return os.path.join(_payload_dir(_trace_dir(work_dir)), f"{event_id}_opencode.log")
