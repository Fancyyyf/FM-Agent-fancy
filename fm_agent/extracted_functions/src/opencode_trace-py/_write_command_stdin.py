# [SPEC]
# Unit: src/opencode_trace-py/_write_command_stdin.py
#
# _write_command_stdin(stream, text) -> None
#
# Pre-condition:
#   - stream is an open, writable stream whose write(s) method accepts a string
#     and whose close() method releases the underlying resource
#   - text is a string to be written to the stream
#
# Post-condition:
#   - text has been written to stream via write(text) and the stream internal
#     buffer has been flushed via flush()
#   - stream.close() has been called — the stream resource is released
#   - The stream is guaranteed to be closed even if write() or flush() raises
#     an exception
# [SPEC]

# [INFO]
# stream.write(text) -> int
#   Pre-condition: text is a string
#   Post-condition: text is written to the stream internal buffer; returns the
#     number of characters written
# [SPLIT]
# stream.flush() -> None
#   Pre-condition: stream is open for writing
#   Post-condition: all buffered data is flushed to the underlying resource
# [SPLIT]
# stream.close() -> None
#   Pre-condition: stream is open
#   Post-condition: stream is closed; further operations on the stream object
#     raise ValueError
# [INFO]

def _write_command_stdin(stream, text):
    try:
        stream.write(text)
        stream.flush()
    finally:
        stream.close()
