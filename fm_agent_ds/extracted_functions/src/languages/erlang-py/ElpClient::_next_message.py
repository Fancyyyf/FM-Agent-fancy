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
