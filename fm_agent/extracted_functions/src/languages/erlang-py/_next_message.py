# [SPEC]
# Unit: src/languages/erlang-py/_next_message.py
#
# ElpClient._next_message(self, deadline: float) -> Any
#
# Pre-condition:
#   - deadline is a monotonic clock time in fractional seconds
#   - self._messages is an active queue that receives parsed JSON-RPC messages
#     from the LSP backend
#
# Post-condition:
#   - Blocks until a message is available from self._messages and returns that message,
#     provided the message is not an instance of BaseException
#   - Raises TimeoutError when the wall-clock monotonic time reaches or exceeds deadline
#     before a message becomes available
#   - Raises RuntimeError when the received message is an instance of BaseException
# [SPEC]

# [INFO]
# self._messages.get(timeout: float) -> Any
#   Pre-condition: timeout is a non-negative number of seconds to wait
#   Post-condition: Blocks until an item is available, then removes and returns
#     that item; raises queue.Empty when timeout seconds elapse before an item
#     becomes available
# [SPLIT]
# time.monotonic() -> float
#   Pre-condition: (none)
#   Post-condition: Returns the current value of a monotonic clock in fractional
#     seconds; successive calls return values that never decrease and are not
#     affected by system clock adjustments
# [INFO]

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
