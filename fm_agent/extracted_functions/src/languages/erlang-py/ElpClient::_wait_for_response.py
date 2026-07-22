# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient._wait_for_response(self, request_id: int, deadline: float) -> Any
#
# Pre-condition:
#   - self is an ElpClient whose underlying JSON-RPC communication channel
#     is open and operational
#   - A request with the given integer request_id was previously transmitted
#     over the same channel
#   - deadline is a monotonic time value representing an absolute time point
#     in the same clock domain as the underlying channel's timeout mechanism
#
# Post-condition:
#   - Blocks the caller, consuming messages from the underlying channel in
#     order until a JSON-RPC response carrying a matching id field arrives
#   - A message is considered a matching response when its "id" field equals
#     request_id and the message lacks a "method" field, distinguishing
#     server responses from server-initiated requests and notifications
#   - Messages received from the server that are not the matching response
#     are forwarded for server-initiated handling and do not cause the
#     function to return
#   - When the underlying channel closes or no message arrives before
#     deadline: raises TimeoutError
#   - When the matching response contains an "error" field:
#       • If the error is a dict whose "code" field equals the transient
#         content-modified error code: raises _ContentModifiedError carrying
#         the error details
#       • Otherwise: raises RuntimeError whose message includes a
#         description of the error
#   - When the matching response contains no "error" field: returns the
#     value of the "result" field from that response
# [SPEC]

# [INFO]
# ElpClient._next_message(self, deadline: float) -> dict
#   Pre-condition: deadline is a monotonic time value representing an
#     absolute time point
#   Post-condition: Blocks until a complete JSON-RPC message arrives from
#     the server or deadline is reached. When a message arrives before
#     deadline, returns the parsed message as a dict. When deadline is
#     reached before a message arrives, raises TimeoutError.
# [SPLIT]
# ElpClient._handle_server_message(self, message: dict)
#   Pre-condition: message is a parsed JSON-RPC message dict received from
#     the server that does not correspond to any pending client request
#   Post-condition: Dispatches the message according to its "method" field
#     and any registered server-message handlers, performing side effects
#     associated with that method. Does not raise to the caller under normal
#     operation.
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
