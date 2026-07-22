# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.request(self, method: str, params: dict | list | None = None) -> Any
#
# Pre-condition:
#   - self is an ElpClient whose underlying JSON-RPC communication channel
#     is open and operational
#   - method is a non-empty string
#   - params, when not None, is a JSON-serializable dict or list
#
# Post-condition:
#   - Transmits a JSON-RPC 2.0 request to the server with the given method
#     and params (where None params is treated as an empty object), tagged
#     with a unique integer identifier that is strictly increasing across
#     successive calls on the same client instance
#   - Blocks the caller until the server returns a response matching that
#     identifier or until the total elapsed time since entry reaches
#     self.timeout seconds, whichever occurs first
#   - On success: returns the value of the "result" field from the matching
#     response
#   - When the server indicates a transient ContentModified error: re-issues
#     the request up to a fixed maximum number of total attempts, bounded in
#     total duration by self.timeout seconds from entry; when all attempts
#     are exhausted without success, raises RuntimeError identifying the
#     failing method
#   - When no matching response arrives before self.timeout seconds elapse
#     from entry: raises TimeoutError
#   - When the server responds with an error whose semantics are not covered
#     by the retry policy: raises RuntimeError
# [SPEC]

# [INFO]
# _send(self, request: dict)
#   Pre-condition: The underlying JSON-RPC output channel is open and
#     writable; request is a dict representing a complete JSON-RPC 2.0
#     request message
#   Post-condition: The request is serialized to JSON and transmitted to the
#     ELP subprocess's standard input using LSP transport protocol framing;
#     on return, the complete frame has been flushed to the input stream
# [SPLIT]
# _wait_for_response(self, request_id: int, deadline: float) -> Any
#   Pre-condition: self is an ElpClient with an open and operational
#     communication channel; a request with the given integer request_id was
#     previously transmitted over the same channel; deadline is a monotonic
#     time value representing an absolute time point
#   Post-condition: Blocks until a JSON-RPC response message carrying a
#     matching id field and no "method" field arrives from the server;
#     returns the value of the "result" field from that response; when the
#     channel closes or no such message arrives before deadline, raises
#     TimeoutError; when the matching response contains an "error" field,
#     raises _ContentModifiedError for transient content-modified errors or
#     RuntimeError otherwise, with error details attached
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
