def append_event(trace_dir, event):
    _ensure_trace_dirs(trace_dir)
    events_path = os.path.join(trace_dir, "events.jsonl")
    line = json.dumps(event, ensure_ascii=False)
    with _LOCK:
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
