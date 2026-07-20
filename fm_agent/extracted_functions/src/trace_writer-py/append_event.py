# [SPEC]
# Unit: src/trace_writer-py/append_event.py
#
# append_event(trace_dir, event) -> None
#
# Pre-condition:
#   - trace_dir is a string specifying a writable filesystem path
#   - event is a dict whose top-level values are JSON-serializable
#
# Post-condition:
#   - The directory trace_dir exists, with any missing parent directories created
#   - The file events.jsonl inside trace_dir has one additional line appended
#   - That line is the JSON serialization of event with non-ASCII characters preserved in their original form (Unicode, not \u-escaped)
#   - The write is safe under concurrency: each event occupies exactly one complete line and bytes from different events are never interleaved within the same line
#   - Returns None
# [SPEC]

# [INFO]
# _ensure_trace_dirs(trace_dir) -> None
#   Pre-condition: trace_dir is a string path
#   Post-condition: the directory trace_dir and all its missing parent directories exist on the filesystem after the call
# [INFO]

def append_event(trace_dir, event):
    _ensure_trace_dirs(trace_dir)
    events_path = os.path.join(trace_dir, "events.jsonl")
    line = json.dumps(event, ensure_ascii=False)
    with _LOCK:
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
