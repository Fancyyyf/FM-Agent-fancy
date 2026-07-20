# [SPEC]
# Unit: src/languages/erlang-py/run.py
#
# run(self) -> None
#
# Pre-condition:
#   - self._stream is an open, readable byte stream sourced from the stdout of a
#     running ELP (Erlang Language Platform) process operating in LSP JSON-RPC
#     mode.
#   - self._messages is a thread-safe queue that accepts any Python object.
#
# Post-condition:
#   - This method never returns; it runs an indefinite loop that consumes LSP
#     JSON-RPC messages from self._stream and places decoded message objects or
#     termination exceptions onto self._messages.
#   - Each complete message consists of a header block (ASCII key-value lines
#     terminated by an empty line) containing a Content-Length field, followed by
#     a body of exactly Content-Length bytes containing a UTF-8-encoded JSON
#     payload.
#   - For each complete message fully received: the JSON payload is decoded and
#     the resulting Python object is placed onto self._messages.
#   - When self._stream reaches EOF before the empty-line terminator of the
#     header block: an EOFError is placed onto self._messages.
#   - When self._stream delivers fewer than Content-Length payload bytes after
#     the header block: an EOFError is placed onto self._messages.
#   - When any BaseException is raised during reading, header parsing, or JSON
#     decoding: the exception object itself (not a wrapper) is placed onto
#     self._messages.
#   - After a termination object (EOFError or other exception) is placed onto
#     self._messages, the method performs no further reads from self._stream and
#     no further puts to self._messages.
# [SPEC]

# [INFO]
# self._stream.readline() -> bytes
#   Pre-condition: stream is open and readable.
#   Post-condition: Returns the next line including its line terminator as bytes,
#     or empty bytes when EOF is reached.
# [SPLIT]
# self._stream.read(n: int) -> bytes
#   Pre-condition: n >= 0; stream is open and readable.
#   Post-condition: Returns up to n bytes from the stream; returns fewer than n
#     bytes only when EOF is reached before all n bytes are available.
# [SPLIT]
# self._messages.put(item) -> None
#   Pre-condition: queue is open for writes.
#   Post-condition: item is appended to the queue; at most one consumer blocked
#     on get() may become unblocked.
# [SPLIT]
# json.loads(s: str) -> object
#   Pre-condition: s is a valid JSON-encoded string.
#   Post-condition: Returns the Python object represented by the JSON string.
# [INFO]

    def run(self):
        try:
            while True:
                headers = {}
                while True:
                    line = self._stream.readline()
                    if not line:
                        raise EOFError("ELP closed its stdout")
                    if line in (b"\r\n", b"\n"):
                        break
                    name, separator, value = line.decode("ascii", "replace").partition(":")
                    if separator:
                        headers[name.strip().lower()] = value.strip()
                length = int(headers["content-length"])
                payload = self._stream.read(length)
                if len(payload) != length:
                    raise EOFError("ELP returned a truncated JSON-RPC payload")
                self._messages.put(json.loads(payload.decode("utf-8")))
        except BaseException as exc:
            self._messages.put(exc)
