# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient._next_message(self, deadline: float)
#
# Pre-condition:
#   - deadline is a point in time expressed as a monotonic clock value
#   - self is an ElpClient whose message reader thread is active and
#     writing parsed JSON-RPC messages into an internal queue
#
# Post-condition:
#   - When a message is available before the monotonic clock reaches
#     deadline, returns the next pending parsed JSON-RPC response or
#     notification message from the server as a dict whose shape conforms
#     to the JSON-RPC 2.0 specification
#   - Raises TimeoutError when no message is available before the
#     monotonic clock reaches deadline, including when the deadline has
#     already passed at call entry
#   - Raises RuntimeError when the message reader thread terminated with
#     an unrecoverable exception; the original exception from the reader
#     thread is chained as the cause of the RuntimeError
# [SPEC]

    def _next_message(self, deadline: float):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("timed out waiting for ELP")
        try:
            message = self._messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError("timed out waiting for ELP") from exc
        if isinstance(message, BaseException):
            raise RuntimeError(str(message)) from message
        return message
