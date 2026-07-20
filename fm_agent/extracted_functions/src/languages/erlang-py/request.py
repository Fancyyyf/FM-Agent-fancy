# [SPEC]
# Unit: src/languages/erlang-py/request.py
#
# ElpClient.request(method: str, params: dict | list | None = None) -> Any
#
# Pre-condition:
#   - self is an ElpClient instance with an active LSP JSON-RPC communication channel
#     (stdin open for writes via self._send, stdout readable for response parsing via
#     self._wait_for_response)
#   - self.timeout is a positive number representing the maximum allowed wall-clock
#     duration in seconds
#   - self._next_id is an integer
#   - method is a non-empty string
#
# Post-condition:
#   - Sends a JSON-RPC 2.0 request to the LSP backend containing the given method,
#     a params object (an empty dict when params is None), and a unique monotonically
#     increasing integer request id
#   - Returns the response result extracted from the backend's JSON-RPC response when
#     the request succeeds before the deadline
#   - When the backend returns a "content modified" error (signaling the document was
#     modified during indexing), the identical request is retried to the same backend
#     after a delay that grows exponentially with each retry attempt, bounded above
#     by 5.0 seconds and by the remaining time before the deadline
#   - Raises RuntimeError when the backend repeatedly returns "content modified" errors
#     for all allowed retry attempts
#   - Raises TimeoutError when self.timeout seconds of wall-clock time have elapsed
#     since the call began without receiving a successful response, or when the
#     remaining time before the deadline is exhausted before the next retry can begin
# [SPEC]

# [INFO]
# self._send(message: dict) -> None
#   Pre-condition: message is a dict, and the JSON-RPC communication channel to the LSP
#     backend process is open
#   Post-condition: Serializes message as a JSON string and writes it to the LSP backend's
#     input stream, preceded by a Content-Length header as required by the LSP protocol
# [SPLIT]
# self._wait_for_response(request_id: int, deadline: float) -> Any
#   Pre-condition: request_id is the integer id of an outstanding JSON-RPC request, and
#     deadline is a monotonic clock time before which a response must arrive
#   Post-condition: Reads and parses JSON-RPC messages from the LSP backend's output
#     stream until a response matching request_id is received; returns the "result"
#     field of that response. Raises _ContentModifiedError when the backend sends a
#     notification or error indicating the document changed during indexing and the
#     request must be retried. Raises an exception when no matching response arrives
#     before deadline.
# [INFO]

    def request(self, method: str, params: dict | list | None = None):
        actual_params = {} if params is None else params
        deadline = time.monotonic() + self.timeout
        for attempt in range(_MAX_CONTENT_MODIFIED_RETRIES):
            request_id = self._next_id
            self._next_id += 1
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": actual_params,
                }
            )
            try:
                return self._wait_for_response(request_id, deadline)
            except _ContentModifiedError as exc:
                if attempt + 1 == _MAX_CONTENT_MODIFIED_RETRIES:
                    raise RuntimeError(
                        f"ELP request {method} repeatedly failed: {exc.error}"
                    ) from exc
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"timed out retrying ELP request {method}") from exc
                time.sleep(min(0.5 * (2**attempt), 5.0, remaining))
        raise AssertionError("unreachable")
