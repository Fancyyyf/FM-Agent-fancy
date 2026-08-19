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
