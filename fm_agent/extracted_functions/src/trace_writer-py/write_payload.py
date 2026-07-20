# [SPEC]
# Unit: src/trace_writer.py
#
# write_payload(trace_dir, event_id, name, content, binary=False) -> str
#
# Pre-condition:
#   - trace_dir is a string path to a writable directory.
#   - event_id is a non-empty string uniquely identifying the owning event.
#   - name is a non-empty string used as a filename component.
#   - content is a string value (or a bytes value when binary is truthy).
#   - binary is a truthy/falsy value.
#
# Post-condition:
#   - The content is atomically written to a file named "{event_id}_{name}"
#     under the payloads subdirectory of trace_dir. The write is atomic: the
#     file either appears at the final path in its entirety or not at all;
#     no partial content is visible at that path.
#   - When binary is falsy, content is written as UTF-8-encoded text.
#   - When binary is truthy, content is written as raw bytes.
#   - Returns a relative path string that identifies the written file for
#     later retrieval. The path is relative to the directory one level above
#     trace_dir and uses the operating-system path separator.
#   - The necessary parent directories for the file are created under
#     trace_dir as a side effect.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
