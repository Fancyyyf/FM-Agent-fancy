# [SPEC]
# Unit: src/opencode_trace-py/_copy_opencode_output.py
#
# _copy_opencode_output(stream, trace_log_path=None) -> None
#
# Pre-condition:
#   - stream is an open, readable stream whose read(n) method returns a string
#     of up to n characters (blocking until data is available) and whose
#     close() method releases the underlying resource
#   - trace_log_path is either None (or a falsy value, meaning no tracing) or
#     a valid writable filesystem path
#
# Post-condition:
#   - All data from stream has been consumed: read(4096) has been called
#     repeatedly until an empty string signals EOF
#   - stream.close() has been called — the stream resource is released
#   - If trace_log_path was truthy, a file at that path exists and contains the
#     complete data read from the stream, encoded in UTF-8 with replacement
#     characters for unencodable data; each chunk is flushed individually
#   - If trace_log_path was falsy, no file is created or written
#   - The trace log file (if opened) is closed before the stream is closed
#   - Regardless of exceptions during reading or writing, both the trace log
#     file (if opened) and the stream are guaranteed to be closed
# [SPEC]

# [INFO]
# open(trace_log_path, "w", encoding="utf-8", errors="replace") -> file
#   Pre-condition: trace_log_path is a writable filesystem path
#   Post-condition: returns an open file for text writing with UTF-8 encoding;
#     unencodable characters are replaced by U+FFFD
# [SPLIT]
# stream.read(4096) -> str
#   Pre-condition: stream is a readable text stream; 4096 is the maximum
#     characters to read per call
#   Post-condition: returns a string of up to 4096 characters; returns ""
#     at EOF
# [SPLIT]
# trace_log.write(chunk) -> int
#   Pre-condition: chunk is a string
#   Post-condition: chunk is written to the file internal buffer; returns the
#     number of characters written
# [SPLIT]
# trace_log.flush() -> None
#   Pre-condition: file is open for writing
#   Post-condition: all buffered data is flushed to the underlying OS file
#     descriptor
# [SPLIT]
# trace_log.close() -> None
#   Pre-condition: file is open
#   Post-condition: file is closed; further operations on the file object
#     raise ValueError
# [SPLIT]
# stream.close() -> None
#   Pre-condition: stream is open
#   Post-condition: stream is closed; further operations on the stream object
#     raise ValueError
# [INFO]

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
