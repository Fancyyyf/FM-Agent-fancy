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
