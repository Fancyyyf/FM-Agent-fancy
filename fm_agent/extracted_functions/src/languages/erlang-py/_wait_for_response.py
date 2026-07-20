# [SPEC]
# Unit: src/languages/erlang-py/request.py
#
# ElpClient._wait_for_response(self, request_id: int, deadline: float) -> Any
#
# Pre-condition:
#   - request_id is the integer id of an outstanding JSON-RPC request sent to
#     the LSP backend
#   - deadline is a monotonic clock time representing the latest wall-clock time
#     by which a matching response must be received
#   - self has an active communication channel with the LSP backend from which
#     JSON-RPC messages can be read
#
# Post-condition:
#   - Reads and parses JSON-RPC messages from the backend's output stream until
#     a response message whose "id" field equals request_id and that lacks a
#     "method" field (i.e., is a response, not a notification) is received
#   - When a matching response is received and contains no error, returns its
#     "result" field
#   - Raises _ContentModifiedError when the matching response contains an error
#     whose code equals the content-modified error code, indicating the document
#     was modified during indexing and the request should be retried by the caller
#   - Raises RuntimeError when the matching response contains any other error
#   - Raises an exception when no matching response arrives before the deadline
#   - Messages that do not match request_id (including server notifications and
#     responses for other requests) are dispatched for side-effect handling and
#     do not prevent continued waiting for the matching response
# [SPEC]

# [INFO]
# ElpClient._next_message(self, deadline: float) -> Any
#   Pre-condition: deadline is a monotonic clock time
#   Post-condition: Blocks until a JSON-RPC message is available from the backend's
#     output stream; returns the parsed message; raises an exception when no message
#     arrives before the deadline
# [SPLIT]
# ElpClient._handle_server_message(self, message: Any) -> None
#   Pre-condition: message is a parsed JSON-RPC message from the backend that does
#     not match the awaited request_id
#   Post-condition: Processes the message according to server-initiated protocol
#     semantics without raising under normal operation
# [INFO]

    def _wait_for_response(self, request_id: int, deadline: float):
        while True:
            message = self._next_message(deadline)
            if message.get("id") == request_id and "method" not in message:
                error = message.get("error")
                if error:
                    if isinstance(error, dict) and error.get("code") == _CONTENT_MODIFIED_ERROR:
                        raise _ContentModifiedError(error)
                    raise RuntimeError(f"ELP request failed: {error}")
                return message.get("result")
            self._handle_server_message(message)
