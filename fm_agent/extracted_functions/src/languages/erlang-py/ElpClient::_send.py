# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient._send(self, message: dict)
#
# Pre-condition:
#   - self._proc is not None and self._proc.stdin is not None and open for
#     writing
#   - message is a dict representing a JSON-serializable JSON-RPC message
#
# Post-condition:
#   - The JSON-serialized form of message is transmitted to the ELP
#     subprocess's standard input using LSP transport protocol framing
#   - The transmitted frame consists of a Content-Length header whose value
#     is the length in bytes of the UTF-8 encoded JSON payload, followed by
#     a CRLF blank line, then the UTF-8 encoded JSON payload itself
#   - The header portion is ASCII-encoded; the payload is compact JSON with
#     no whitespace between keys, values, colons, or commas, and all non-ASCII
#     characters are preserved in their original form
#   - Transmission is atomic with respect to other concurrent _send calls on
#     the same client instance
#   - On return, the complete frame has been delivered to the subprocess's
#     input stream (the write has been flushed to the OS pipe)
#   - Raises RuntimeError when the ELP subprocess is not running or its
#     standard input is unavailable
# [SPEC]

# [INFO]
# self._proc.stdin.write(data: bytes)
#   Pre-condition: The subprocess stdin pipe associated with self._proc is
#     open and writable; data is a bytes object
#   Post-condition: data is buffered for delivery to the subprocess's standard
#     input
# [SPLIT]
# self._proc.stdin.flush()
#   Pre-condition: self._proc.stdin is a _StdoutTee whose _console is an open,
#     writable stream that supports flush, and whose _log_stream is a writable
#     stream (may be closed) that supports flush
#   Post-condition: All buffered data written via this tee's write operations
#     is pushed to the console; data is pushed to the log stream if and only if
#     the log stream is open; no exception is raised if the log stream is
#     closed, and the console flush succeeds regardless
# [INFO]

    def _send(self, message: dict):
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("ELP client is not running")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        frame = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload
        with self._write_lock:
            self._proc.stdin.write(frame)
            self._proc.stdin.flush()
