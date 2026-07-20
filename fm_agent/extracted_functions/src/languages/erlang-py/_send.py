# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/_send.py
#
# ElpClient._send(self, message: dict) -> None
#
# Pre-condition:
#   - self is an ElpClient instance
#   - message is a dict representing a JSON-RPC message to be transmitted to the LSP
#     backend
#   - The LSP backend process is running and its standard input stream is open for
#     writing
#
# Post-condition:
#   - The message dict is serialized to a valid JSON string and encoded as UTF-8
#   - The encoded payload is transmitted to the backend process's standard input,
#     preceded by an LSP protocol Content-Length header whose value equals the
#     length of the encoded payload in bytes, followed by a CRLF-delimited blank
#     separator line
#   - The backend's standard input stream is flushed after transmission, ensuring
#     the backend can read the message without delay
#   - Raises RuntimeError when the backend process is None or its stdin stream is
#     None (backend is not running)
#   - Raises an exception when the write to or flush of the backend's stdin fails
#     (communication channel failure)
#   - The entire framed message is written atomically with respect to other
#     concurrent calls to this method on the same instance: no interleaving of
#     bytes between concurrent senders
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _send(self, message: dict):
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("ELP client is not running")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        frame = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload
        with self._write_lock:
            self._proc.stdin.write(frame)
            self._proc.stdin.flush()
